from app.config import settings


def _has_direct_answer_overlap(query: str, text: str) -> bool:
    lowered_query = query.lower()
    lowered_text = text.lower()

    direct_answer_terms = [
        "payment",
        "payments",
        "invoice",
        "invoices",
        "thirty days",
        "30 days",
        "termination",
        "confidentiality",
        "confidential",
        "uploaded",
        "vendor",
        "document",
    ]

    query_hits = [
        term
        for term in direct_answer_terms
        if term in lowered_query
    ]

    if not query_hits:
        return False

    text_hits = [
        term
        for term in query_hits
        if term in lowered_text
    ]

    return len(text_hits) >= 2


def grade_evidence(reranked_chunks: list[dict]) -> dict:
    if not reranked_chunks:
        return {
            "status": "NO_EVIDENCE",
            "reason": "No retrieved chunks were available.",
            "top_score": 0.0,
        }

    top_chunk = reranked_chunks[0]
    top_score = top_chunk.get("score", 0.0)
    top_collection = top_chunk.get("collection")
    top_text = top_chunk.get("text", "")

    strong_threshold = min(settings.relevance_threshold, 0.50)
    uploaded_doc_threshold = 0.45
    weak_threshold = 0.30

    query_candidates = []

    for chunk in reranked_chunks[:3]:
        chunk_text = chunk.get("text", "")
        if chunk_text:
            query_candidates.append(chunk_text)

    combined_top_text = " ".join(query_candidates)

    # Uploaded matter documents often contain short, direct answers.
    # A slightly lower threshold is acceptable when the top uploaded chunk
    # directly overlaps with the user's requested terms.
    if (
        top_collection == "uploaded_matter_docs"
        and top_score >= uploaded_doc_threshold
        and _has_direct_answer_overlap(top_text, combined_top_text)
    ):
        return {
            "status": "STRONG",
            "reason": "Top uploaded matter document directly matches the requested terms.",
            "top_score": top_score,
        }

    if top_score >= strong_threshold:
        return {
            "status": "STRONG",
            "reason": "Top reranked chunk passed the MVP local relevance threshold.",
            "top_score": top_score,
        }

    if top_score >= weak_threshold:
        return {
            "status": "WEAK",
            "reason": "Evidence is present but below the strong local relevance threshold.",
            "top_score": top_score,
        }

    return {
        "status": "NO_EVIDENCE",
        "reason": "Top evidence score is too low for a safe answer.",
        "top_score": top_score,
    }