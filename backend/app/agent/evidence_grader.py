from app.config import settings


def _contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _has_direct_fact_match(text: str) -> bool:
    lowered = text.lower()

    payment_terms = [
        "payment",
        "payments",
        "invoice",
        "invoices",
        "net 30",
        "thirty days",
        "30 days",
        "receipt",
        "due",
    ]

    document_terms = [
        "uploaded",
        "original file type",
        ".csv",
        ".xlsx",
        ".pdf",
        ".docx",
        "row ",
        "sheet:",
        "page ",
        "document id:",
        "title:",
    ]

    legal_business_terms = [
        "termination",
        "confidentiality",
        "confidential",
        "vendor",
        "agreement",
        "customer",
        "pricing",
    ]

    payment_hits = sum(1 for term in payment_terms if term in lowered)
    document_hits = sum(1 for term in document_terms if term in lowered)
    legal_business_hits = sum(1 for term in legal_business_terms if term in lowered)

    if payment_hits >= 2 and document_hits >= 1:
        return True

    if payment_hits >= 2 and legal_business_hits >= 1:
        return True

    return False


def grade_evidence(reranked_chunks: list[dict]) -> dict:
    if not reranked_chunks:
        return {
            "status": "NO_EVIDENCE",
            "reason": "No retrieved chunks were available.",
            "top_score": 0.0,
        }

    top_chunk = reranked_chunks[0]
    top_score = top_chunk.get("score", 0.0) or 0.0
    top_collection = top_chunk.get("collection")
    top_source_type = top_chunk.get("source_type")
    top_text = top_chunk.get("text", "")

    strong_threshold = min(settings.relevance_threshold, 0.50)
    uploaded_doc_threshold = 0.30
    weak_threshold = 0.20

    if (
        top_collection == "uploaded_matter_docs"
        and top_score >= uploaded_doc_threshold
        and _has_direct_fact_match(top_text)
    ):
        return {
            "status": "STRONG",
            "reason": "Top uploaded matter document contains direct factual terms matching the question.",
            "top_score": top_score,
        }

    if (
        top_source_type in {"uploaded_txt", "uploaded_csv", "uploaded_xlsx", "uploaded_pdf", "uploaded_docx"}
        and top_score >= uploaded_doc_threshold
        and _has_direct_fact_match(top_text)
    ):
        return {
            "status": "STRONG",
            "reason": "Top uploaded file contains direct factual terms matching the question.",
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