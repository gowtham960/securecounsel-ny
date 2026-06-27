from rank_bm25 import BM25Okapi

from app.retrieval.local_search import (
    filter_authorized_chunks,
    get_local_chunks,
    lexical_score,
    tokenize,
)


def _fallback_lexical_search(
    query: str,
    authorized_chunks: list[dict],
    limit: int = 5,
) -> list[dict]:
    scored_results = []

    for chunk in authorized_chunks:
        score = lexical_score(query, chunk.get("text", ""))

        if score <= 0:
            continue

        scored_results.append(
            {
                **chunk,
                "score": round(score, 4),
                "retrieval_method": "bm25_fallback_lexical",
            }
        )

    return sorted(
        scored_results,
        key=lambda item: item["score"],
        reverse=True,
    )[:limit]


def bm25_keyword_search(
    query: str,
    source: str,
    firm_id: str,
    matter_id: str | None,
) -> list[dict]:
    """
    Local sparse retrieval.

    Primary path:
    - rank-bm25 BM25Okapi

    Fallback path:
    - lexical scorer for very small corpora where BM25 may return no positive hits.
    """
    authorized_chunks = filter_authorized_chunks(
        chunks=get_local_chunks(),
        source=source,
        firm_id=firm_id,
        matter_id=matter_id,
    )

    if not authorized_chunks:
        return []

    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    tokenized_corpus = [
        tokenize(chunk.get("text", ""))
        for chunk in authorized_chunks
    ]

    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(query_tokens)

    positive_scores = [float(score) for score in scores if score > 0]

    if not positive_scores:
        return _fallback_lexical_search(
            query=query,
            authorized_chunks=authorized_chunks,
        )

    max_score = max(positive_scores)

    scored_results = []

    for chunk, score in zip(authorized_chunks, scores):
        score = float(score)

        if score <= 0:
            continue

        normalized_score = score / max_score if max_score > 0 else 0.0

        scored_results.append(
            {
                **chunk,
                "score": round(normalized_score, 4),
                "retrieval_method": "bm25_rank_bm25",
            }
        )

    if not scored_results:
        return _fallback_lexical_search(
            query=query,
            authorized_chunks=authorized_chunks,
        )

    return sorted(
        scored_results,
        key=lambda item: item["score"],
        reverse=True,
    )[:5]