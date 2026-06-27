from app.config import settings


def grade_evidence(reranked_chunks: list[dict]) -> dict:
    if not reranked_chunks:
        return {
            "status": "NO_EVIDENCE",
            "reason": "No retrieved chunks were available.",
            "top_score": 0.0,
        }

    top_score = reranked_chunks[0].get("score", 0.0)

    strong_threshold = min(settings.relevance_threshold, 0.50)
    weak_threshold = 0.30

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