from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
UPLOADED_DOCS_DIR = DATA_DIR / "uploaded_docs"


def chunk_text(text: str, max_words: int = 90, overlap_words: int = 20) -> list[str]:
    words = text.split()

    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = start + max_words
        chunk = " ".join(words[start:end])
        chunks.append(chunk)

        if end >= len(words):
            break

        start = max(0, end - overlap_words)

    return chunks


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_field(text: str, field_name: str, default: str | None = None) -> str | None:
    prefix = f"{field_name}:"

    for line in text.splitlines():
        if line.startswith(prefix):
            return line.replace(prefix, "", 1).strip()

    return default


def _load_seed_documents() -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []

    source_configs = [
        {
            "folder": DATA_DIR / "private_docs",
            "collection": "private_matter_docs",
            "default_source_type": "contract",
        },
        {
            "folder": DATA_DIR / "firm_kb",
            "collection": "firm_knowledge_base",
            "default_source_type": "playbook",
        },
        {
            "folder": DATA_DIR / "ny_authorities",
            "collection": "ny_legal_authorities",
            "default_source_type": "statute",
        },
    ]

    for config in source_configs:
        folder = config["folder"]

        if not folder.exists():
            continue

        for path in folder.glob("*.txt"):
            text = _read_text_file(path)

            document_id = _extract_field(text, "Document ID", path.stem)
            firm_id = _extract_field(text, "Firm ID", "firm_demo")
            matter_id = _extract_field(text, "Matter ID")
            citation = _extract_field(text, "Citation")
            title = _extract_field(text, "Title", path.stem.replace("_", " ").title())

            documents.append(
                {
                    "collection": config["collection"],
                    "document_id": document_id,
                    "firm_id": firm_id,
                    "matter_id": matter_id,
                    "citation": citation or title,
                    "title": title,
                    "source_type": config["default_source_type"],
                    "text": text,
                    "path": str(path),
                }
            )

    return documents


def _load_uploaded_txt_documents() -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []

    if not UPLOADED_DOCS_DIR.exists():
        return documents

    for matter_folder in UPLOADED_DOCS_DIR.iterdir():
        if not matter_folder.is_dir():
            continue

        matter_id = matter_folder.name

        for path in matter_folder.glob("*.txt"):
            text = _read_text_file(path)

            document_id = path.stem
            title = path.name

            documents.append(
                {
                    "collection": "uploaded_matter_docs",
                    "document_id": document_id,
                    "firm_id": "firm_demo",
                    "matter_id": matter_id,
                    "citation": f"Uploaded document: {path.name}",
                    "title": title,
                    "source_type": "uploaded_txt",
                    "text": text,
                    "path": str(path),
                }
            )

    return documents


def load_local_documents() -> list[dict[str, Any]]:
    return _load_seed_documents() + _load_uploaded_txt_documents()


def build_local_chunks() -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    for document in load_local_documents():
        text_chunks = chunk_text(document["text"])

        for index, text in enumerate(text_chunks, start=1):
            chunks.append(
                {
                    "collection": document["collection"],
                    "document_id": document["document_id"],
                    "chunk_id": f"{document['document_id']}_chunk_{index:03d}",
                    "firm_id": document.get("firm_id"),
                    "matter_id": document.get("matter_id"),
                    "source_type": document.get("source_type"),
                    "citation": document.get("citation"),
                    "title": document.get("title"),
                    "text": text,
                    "score": 0.0,
                    "retrieval_method": "local_index",
                }
            )

    return chunks