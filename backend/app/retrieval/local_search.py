import math
import re
from collections import Counter

from app.ingestion.local_index import build_local_chunks


_LOCAL_CHUNKS_CACHE: list[dict] | None = None


def get_local_chunks() -> list[dict]:
    global _LOCAL_CHUNKS_CACHE

    if _LOCAL_CHUNKS_CACHE is None:
        _LOCAL_CHUNKS_CACHE = build_local_chunks()

    return _LOCAL_CHUNKS_CACHE


def reset_local_chunks_cache() -> None:
    global _LOCAL_CHUNKS_CACHE
    _LOCAL_CHUNKS_CACHE = None


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9\-]+", text.lower())


def lexical_score(query: str, text: str) -> float:
    query_tokens = tokenize(query)
    text_tokens = tokenize(text)

    if not query_tokens or not text_tokens:
        return 0.0

    text_counts = Counter(text_tokens)
    query_counts = Counter(query_tokens)

    overlap = 0.0

    for token, query_count in query_counts.items():
        if token in text_counts:
            overlap += min(query_count, text_counts[token])

    normalized = overlap / math.sqrt(len(query_tokens) * len(text_tokens))

    phrase_boost = 0.0
    lowered_text = text.lower()
    lowered_query = query.lower()

    important_phrases = [
        "non-compete",
        "new york",
        "termination",
        "confidential information",
        "non-solicitation",
        "restrictive covenant",
    ]

    for phrase in important_phrases:
        if phrase in lowered_query and phrase in lowered_text:
            phrase_boost += 0.15

    return min(1.0, normalized + phrase_boost)


def filter_authorized_chunks(
    chunks: list[dict],
    source: str,
    firm_id: str,
    matter_id: str | None,
) -> list[dict]:
    authorized = []

    for chunk in chunks:
        if chunk.get("collection") != source:
            continue

        if chunk.get("firm_id") not in {None, firm_id}:
            continue

        if source == "private_matter_docs":
            if not matter_id:
                continue

            if chunk.get("matter_id") != matter_id:
                continue

        authorized.append(chunk)

    return authorized


def local_keyword_search(
    query: str,
    source: str,
    firm_id: str,
    matter_id: str | None,
    limit: int = 5,
) -> list[dict]:
    chunks = filter_authorized_chunks(
        chunks=get_local_chunks(),
        source=source,
        firm_id=firm_id,
        matter_id=matter_id,
    )

    scored = []

    for chunk in chunks:
        score = lexical_score(query, chunk["text"])

        if score <= 0:
            continue

        scored.append(
            {
                **chunk,
                "score": round(score, 4),
                "retrieval_method": "local_keyword",
            }
        )

    return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]