from app.retrieval.local_search import lexical_score


def _source_boost(query: str, chunk: dict) -> float:
    lowered = query.lower()
    collection = chunk.get("collection")

    boost = 0.0

    if collection == "private_matter_docs":
        if any(term in lowered for term in ["agreement", "contract", "clause", "employee", "john smith"]):
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
    ]

    for phrase in important_phrases:
        if phrase in lowered_query and phrase in lowered_text:
            boost += 0.15

    return boost


def rerank_chunks(query: str, chunks: list[dict]) -> list[dict]:
    """
    MVP reranker.

    Combines:
    - original retrieval score
    - RRF fusion score
    - lexical similarity
    - source-aware boost
    - phrase boost

    Later this becomes Cohere Rerank.
    """
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
                "rerank_debug": {
                    "original_score": original_score,
                    "fusion_score": fusion_score,
                    "lexical_score": round(lexical, 4),
                    "source_boost": round(source, 4),
                    "phrase_boost": round(phrase, 4),
                },
            }
        )

    return sorted(
        reranked,
        key=lambda item: item.get("score", 0.0),
        reverse=True,
    )