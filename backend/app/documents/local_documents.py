from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


UPLOAD_ROOT = Path("data") / "uploaded_docs"

DOCUMENT_REGISTRY: list[dict] = []


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_upload_folder(matter_id: str) -> Path:
    folder = UPLOAD_ROOT / matter_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def sanitize_filename(filename: str) -> str:
    safe = filename.replace("\\", "_").replace("/", "_").strip()
    if not safe:
        safe = "uploaded_document.txt"
    return safe


def save_uploaded_text_document(
    matter_id: str,
    uploaded_by: str,
    filename: str,
    content: bytes,
) -> dict:
    safe_name = sanitize_filename(filename)

    if not safe_name.lower().endswith(".txt"):
        raise ValueError("Only .txt files are supported in the current MVP.")

    document_id = "doc_upload_" + uuid4().hex[:12]
    folder = ensure_upload_folder(matter_id)
    stored_filename = f"{document_id}_{safe_name}"
    stored_path = folder / stored_filename

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("Uploaded .txt file must be UTF-8 encoded.")

    stored_path.write_text(text, encoding="utf-8")

    document = {
        "document_id": document_id,
        "matter_id": matter_id,
        "filename": safe_name,
        "stored_path": str(stored_path),
        "uploaded_by": uploaded_by,
        "uploaded_at": utc_now_iso(),
        "content_type": "text/plain",
        "status": "uploaded",
        "size_bytes": len(content),
    }

    DOCUMENT_REGISTRY.append(document)
    return document


def list_documents_for_matter(matter_id: str) -> list[dict]:
    return [
        document
        for document in DOCUMENT_REGISTRY
        if document["matter_id"] == matter_id
    ]