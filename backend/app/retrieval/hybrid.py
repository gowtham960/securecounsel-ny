from app.retrieval.dense_qdrant import dense_vector_search
from app.retrieval.sparse_bm25 import bm25_keyword_search
from app.retrieval.fusion import reciprocal_rank_fusion


def hybrid_retrieve(
    source_queries: dict[str, list[str]],
    sources_needed: list[str],
    firm_id: str,
    matter_id: str | None,
) -> dict:
    dense_results: list[dict] = []
    bm25_results: list[dict] = []

    source_query_map = {
        "private_matter_docs": source_queries.get("private_queries", []),
        "firm_knowledge_base": source_queries.get("firm_kb_queries", []),
        "ny_legal_authorities": source_queries.get("ny_legal_queries", []),
    }

    for source in sources_needed:
        queries = source_query_map.get(source, [])

        for query in queries:
            dense_results.extend(
                dense_vector_search(
                    query=query,
                    source=source,
                    firm_id=firm_id,
                    matter_id=matter_id,
                )
            )

            bm25_results.extend(
                bm25_keyword_search(
                    query=query,
                    source=source,
                    firm_id=firm_id,
                    matter_id=matter_id,
                )
            )

    fused_results = reciprocal_rank_fusion(
        dense_results=dense_results,
        bm25_results=bm25_results,
    )

    return {
        "dense_results": dense_results,
        "bm25_results": bm25_results,
        "fused_results": fused_results,
    }