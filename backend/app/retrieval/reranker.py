import os

from dotenv import load_dotenv

from app.retrieval.local_search import lexical_score


load_dotenv()


def _source_boost(query: str, chunk: dict) -> float:
    lowered = query.lower()
    collection = chunk.get("collection")

    boost = 0.0

    if collection == "private_matter_docs":
        if any(
            term in lowered
            for term in ["agreement", "contract", "clause", "employee", "john smith"]
        ):
            boost += 0.20

    if collection == "uploaded_matter_docs":
        if any(
            term in lowered
            for term in [
                "payment",
                "invoice",
                "invoices",
                "due",
                "csv",
                "xlsx",
                "upload",
                "uploaded",
                "document",
            ]
        ):
            boost += 0.20

    if collection == "firm_knowledge_base":
        if any(term in lowered for term in ["risk", "review", "playbook", "standard", "factors"]):
            boost += 0.10

    if collection == "ny_legal_authorities":
        if any(term in lowered for term in ["law", "statute", "new york", "ny", "legal authority"]):
            boost += 0.15

    return boost


def _phrase_boost(query: str, chunk: dict) -> float:
    lowered_query = query.lower()
    lowered_text = chunk.get("text", "").lower()

    boost = 0.0

    important_phrases = [
        "non-solicitation",
        "non-compete",
        "confidential information",
        "termination",
        "new york state",
        "legitimate business interest",
        "narrowly tailored",
        "payment terms",
        "invoice due",
        "invoices due",
        "thirty days",
        "30 days",
        "net 30",
    ]

    for phrase in important_phrases:
        if phrase in lowered_query and phrase in lowered_text:
            boost += 0.15

    return boost


def _local_rerank_chunks(query: str, chunks: list[dict]) -> list[dict]:
    reranked = []

    for chunk in chunks:
        original_score = float(chunk.get("score", 0.0))
        fusion_score = float(chunk.get("fusion_score", 0.0))
        lexical = lexical_score(query, chunk.get("text", ""))
        source = _source_boost(query, chunk)
        phrase = _phrase_boost(query, chunk)

        rerank_score = (
            original_score * 0.45
            + lexical * 0.30
            + fusion_score * 2.0
            + source
            + phrase
        )

        reranked.append(
            {
                **chunk,
                "score": round(rerank_score, 4),
                "rerank_model": "local_heuristic",
                "rerank_debug": {
                    "original_score": original_score,
                    "fusion_score": fusion_score,
                    "lexical_score": round(lexical, 4),
                    "source_boost": round(source, 4),
                    "phrase_boost": round(phrase, 4),
                    "score_source": "cohere_normalized_max",
                },
            }
        )

    return sorted(
        reranked,
        key=lambda item: item.get("score", 0.0),
        reverse=True,
    )


def _cohere_rerank_chunks(query: str, chunks: list[dict]) -> list[dict] | None:
    api_key = os.getenv("COHERE_API_KEY")

    if not api_key:
        return None

    try:
        import cohere

        client = cohere.Client(api_key)

        documents = []

        for chunk in chunks:
            documents.append(
                "\n".join(
                    [
                        f"Title: {chunk.get('title') or ''}",
                        f"Citation: {chunk.get('citation') or ''}",
                        f"Collection: {chunk.get('collection') or ''}",
                        f"Source Type: {chunk.get('source_type') or ''}",
                        f"Text: {chunk.get('text') or ''}",
                    ]
                )
            )

        model = os.getenv("COHERE_RERANK_MODEL", "rerank-v3.5")

        response = client.rerank(
            model=model,
            query=query,
            documents=documents,
            top_n=len(documents),
        )

        cohere_results = getattr(response, "results", [])

        reranked = []

        for rank, result in enumerate(cohere_results, start=1):
            index = getattr(result, "index", None)
            relevance_score = getattr(result, "relevance_score", None)

            if index is None or relevance_score is None:
                continue

            chunk = chunks[index]
            original_score = float(chunk.get("score", 0.0))
            fusion_score = float(chunk.get("fusion_score", 0.0))
            cohere_score = float(relevance_score)

            combined_score = max(cohere_score,original_score * 0.45 + fusion_score * 2.0,
                )

            reranked.append(
                {
                    **chunk,
                    "score": round(combined_score, 4),
                    "rerank_model": model,
                    "rerank_debug": {
                        "cohere_relevance_score": round(cohere_score, 4),
                        "original_score": original_score,
                        "fusion_score": fusion_score,
                        "rank": rank,
                    },
                }
            )

        if not reranked:
            return None

        return sorted(
            reranked,
            key=lambda item: item.get("score", 0.0),
            reverse=True,
        )

    except Exception as exc:
        print(f"[reranker] Cohere rerank failed: {exc}")
        return None


def rerank_chunks(query: str, chunks: list[dict]) -> list[dict]:
    """
    Rerank retrieved chunks.

    Uses Cohere Rerank when COHERE_API_KEY is available.
    Falls back to the local heuristic reranker when Cohere is missing or fails.
    """
    if not chunks:
        return []

    cohere_reranked = _cohere_rerank_chunks(query, chunks)

    if cohere_reranked is not None:
        return cohere_reranked

    return _local_rerank_chunks(query, chunks)