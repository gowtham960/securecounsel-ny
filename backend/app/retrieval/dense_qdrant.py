from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
    PayloadSchemaType
)
import uuid
from app.config import settings

_client: QdrantClient | None = None
_model: SentenceTransformer | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )
    return _client


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print("[qdrant] Loading embedding model...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        print("[qdrant] Embedding model loaded.")
    return _model


def _create_payload_indexes():
    client = get_client()
    for field in ["firm_id", "matter_id", "collection"]:
        try:
            client.create_payload_index(
                collection_name=settings.qdrant_collection,
                field_name=field,
                field_schema=PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass  # index may already exist
    print("[qdrant] Payload indexes ready.")


def ensure_collection():
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]
    if settings.qdrant_collection not in existing:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        print(f"[qdrant] Created collection: {settings.qdrant_collection}")
    _create_payload_indexes()


def upsert_chunks(chunks: list[dict]):
    """Index a list of chunks into Qdrant. Each chunk must have 'text' and 'metadata'."""
    ensure_collection()
    model = get_model()
    client = get_client()

    texts = [c["text"] for c in chunks]
    vectors = model.encode(texts, show_progress_bar=False).tolist()

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vectors[i],
            payload={"text": chunks[i]["text"], **chunks[i].get("metadata", {})}
        )
        for i in range(len(chunks))
    ]

    client.upsert(collection_name=settings.qdrant_collection, points=points)
    print(f"[qdrant] Upserted {len(points)} chunks.")


def dense_vector_search(
    query: str,
    source: str,
    firm_id: str,
    matter_id: str | None,
    limit: int = 5,
) -> list[dict]:
    """Semantic vector search against Qdrant."""
    try:
        ensure_collection()
        model = get_model()
        client = get_client()

        query_vector = model.encode([query])[0].tolist()

        must = [
            FieldCondition(key="firm_id", match=MatchValue(value=firm_id)),
            FieldCondition(key="collection", match=MatchValue(value=source)),
        ]
        if matter_id:
            must.append(
                FieldCondition(key="matter_id", match=MatchValue(value=matter_id))
            )

        results = client.query_points(
            collection_name=settings.qdrant_collection,
            query=query_vector,
            query_filter=Filter(must=must),
            limit=limit,
            with_payload=True,
        ).points

        return [
            {
                "text": r.payload.get("text", ""),
                "score": round(r.score, 4),
                "collection": r.payload.get("collection", source),
                "document_id": r.payload.get("document_id", ""),
                "chunk_id": r.payload.get("chunk_id", ""),
                "firm_id": r.payload.get("firm_id", firm_id),
                "matter_id": r.payload.get("matter_id"),
                "source_type": r.payload.get("source_type", ""),
                "citation": r.payload.get("citation", ""),
                "title": r.payload.get("title", ""),
                "retrieval_method": "dense_qdrant",
            }
            for r in results
        ]

    except Exception as e:
        print(f"[qdrant] dense_vector_search failed: {e}")
        return []