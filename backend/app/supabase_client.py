import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")


def get_supabase_key() -> str | None:
    return SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY


def supabase_is_configured() -> bool:
    return bool(SUPABASE_URL and get_supabase_key())


def _headers(extra: dict | None = None) -> dict:
    api_key = get_supabase_key()

    headers = {
        "apikey": api_key or "",
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    if extra:
        headers.update(extra)

    return headers


def _table_url(table_name: str, query: dict | None = None) -> str:
    base_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table_name}"

    if not query:
        return base_url

    return f"{base_url}?{urlencode(query)}"


def supabase_select(table_name: str, query: dict | None = None) -> list[dict]:
    if not supabase_is_configured():
        return []

    request = Request(
        _table_url(table_name, query),
        method="GET",
        headers=_headers(),
    )

    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def supabase_upsert(table_name: str, rows: list[dict], on_conflict: str) -> list[dict]:
    if not supabase_is_configured():
        return []

    request = Request(
        _table_url(table_name, {"on_conflict": on_conflict}),
        method="POST",
        headers=_headers(
            {
                "Prefer": "resolution=merge-duplicates,return=representation",
            }
        ),
        data=json.dumps(rows).encode("utf-8"),
    )

    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def supabase_insert(table_name: str, row: dict) -> dict | None:
    if not supabase_is_configured():
        return None

    request = Request(
        _table_url(table_name),
        method="POST",
        headers=_headers(
            {
                "Prefer": "return=representation",
            }
        ),
        data=json.dumps(row).encode("utf-8"),
    )

    with urlopen(request, timeout=10) as response:
        rows = json.loads(response.read().decode("utf-8"))

    if not rows:
        return None

    return rows[0]


def supabase_delete(table_name: str, query: dict) -> bool:
    if not supabase_is_configured():
        return False

    request = Request(
        _table_url(table_name, query),
        method="DELETE",
        headers=_headers(),
    )

    with urlopen(request, timeout=10):
        return True