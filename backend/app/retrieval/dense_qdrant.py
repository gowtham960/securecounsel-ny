from app.retrieval.local_search import local_keyword_search


def dense_vector_search(
    query: str,
    source: str,
    firm_id: str,
    matter_id: str | None,
) -> list[dict]:
    """
    MVP placeholder for dense semantic vector search.

    For now, this uses local keyword scoring so the app searches real local files.
    Later this file will call Qdrant using query embeddings.
    """
    results = local_keyword_search(
        query=query,
        source=source,
        firm_id=firm_id,
        matter_id=matter_id,
        limit=5,
    )

    return [
        {
            **item,
            "retrieval_method": "dense_placeholder_local",
            "score": min(1.0, item.get("score", 0.0) + 0.08),
        }
        for item in results
    ]