from datetime import datetime, timezone
from uuid import uuid4

from app.supabase_client import (
    supabase_delete,
    supabase_insert,
    supabase_select,
    supabase_upsert,
)


MATTERS_TABLE = "demo_matters"
ASSIGNMENTS_TABLE = "demo_matter_assignments"


DEMO_MATTERS = {
    "matter_acme_smith": {
        "matter_id": "matter_acme_smith",
        "matter_name": "ACME v. Smith Employment Agreement",
        "client_name": "ACME Corp",
        "matter_type": "Employment Agreement Review",
        "status": "Active",
        "description": "Review of John Smith employment agreement, including restrictive covenant, confidentiality, termination, and non-solicitation provisions.",
        "primary_document": "John Smith Employment Agreement",
        "created_by": "admin@demo-law.com",
        "created_at": "2026-06-27T00:00:00Z",
    },
    "matter_omega_contract": {
        "matter_id": "matter_omega_contract",
        "matter_name": "Omega Contract Review",
        "client_name": "Omega Holdings",
        "matter_type": "Commercial Contract Review",
        "status": "Active",
        "description": "Commercial contract review workspace for vendor obligations, termination rights, and risk allocation.",
        "primary_document": "Omega Commercial Agreement",
        "created_by": "admin@demo-law.com",
        "created_at": "2026-06-27T00:00:00Z",
    },
    "matter_secret_case": {
        "matter_id": "matter_secret_case",
        "matter_name": "Confidential Internal Investigation",
        "client_name": "Confidential Client",
        "matter_type": "Internal Investigation",
        "status": "Restricted",
        "description": "Restricted internal investigation matter visible only to Firm Admin in demo mode.",
        "primary_document": "Restricted Investigation File",
        "created_by": "admin@demo-law.com",
        "created_at": "2026-06-27T00:00:00Z",
    },
}


DEMO_MATTER_ASSIGNMENTS = [
    {
        "assignment_id": "assign_attorney_acme",
        "user_email": "attorney@demo-law.com",
        "matter_id": "matter_acme_smith",
        "assigned_role": "Attorney",
        "assigned_by": "admin@demo-law.com",
        "assigned_at": "2026-06-27T00:00:00Z",
    },
    {
        "assignment_id": "assign_attorney_omega",
        "user_email": "attorney@demo-law.com",
        "matter_id": "matter_omega_contract",
        "assigned_role": "Attorney",
        "assigned_by": "admin@demo-law.com",
        "assigned_at": "2026-06-27T00:00:00Z",
    },
    {
        "assignment_id": "assign_paralegal_acme",
        "user_email": "paralegal@demo-law.com",
        "matter_id": "matter_acme_smith",
        "assigned_role": "Paralegal",
        "assigned_by": "admin@demo-law.com",
        "assigned_at": "2026-06-27T00:00:00Z",
    },
]


_SUPABASE_SEEDED = False


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _seed_supabase_demo_data() -> None:
    global _SUPABASE_SEEDED

    if _SUPABASE_SEEDED:
        return

    try:
        supabase_upsert(
            table_name=MATTERS_TABLE,
            rows=list(DEMO_MATTERS.values()),
            on_conflict="matter_id",
        )
        supabase_upsert(
            table_name=ASSIGNMENTS_TABLE,
            rows=DEMO_MATTER_ASSIGNMENTS,
            on_conflict="user_email,matter_id",
        )
        _SUPABASE_SEEDED = True
    except Exception as exc:
        print(f"[matters] Supabase seed skipped: {exc}")


def _supabase_matters() -> list[dict]:
    try:
        _seed_supabase_demo_data()
        rows = supabase_select(
            MATTERS_TABLE,
            {
                "select": "*",
                "order": "created_at.asc",
            },
        )
        return rows
    except Exception as exc:
        print(f"[matters] Supabase matter read failed: {exc}")
        return []


def _supabase_assignments() -> list[dict]:
    try:
        _seed_supabase_demo_data()
        rows = supabase_select(
            ASSIGNMENTS_TABLE,
            {
                "select": "*",
                "order": "assigned_at.asc",
            },
        )
        return rows
    except Exception as exc:
        print(f"[matters] Supabase assignment read failed: {exc}")
        return []


def list_all_matters() -> list[dict]:
    rows = _supabase_matters()

    if rows:
        return rows

    return list(DEMO_MATTERS.values())


def list_all_assignments() -> list[dict]:
    rows = _supabase_assignments()

    if rows:
        return rows

    return DEMO_MATTER_ASSIGNMENTS


def list_assigned_matter_ids_for_user(user_email: str) -> list[str]:
    return [
        assignment["matter_id"]
        for assignment in list_all_assignments()
        if assignment["user_email"] == user_email
    ]


def list_matters_for_user(user: dict) -> list[dict]:
    if user["role"] == "Firm Admin":
        return list_all_matters()

    assigned_matter_ids = set(list_assigned_matter_ids_for_user(user["user_email"]))

    return [
        matter
        for matter in list_all_matters()
        if matter["matter_id"] in assigned_matter_ids
    ]


def get_matter_for_user(user: dict, matter_id: str) -> dict | None:
    matters_by_id = {
        matter["matter_id"]: matter
        for matter in list_all_matters()
    }

    if user["role"] == "Firm Admin":
        return matters_by_id.get(matter_id)

    assigned_matter_ids = set(list_assigned_matter_ids_for_user(user["user_email"]))

    if matter_id not in assigned_matter_ids:
        return None

    return matters_by_id.get(matter_id)


def create_demo_matter(
    matter_name: str,
    client_name: str,
    matter_type: str,
    status: str,
    description: str,
    primary_document: str,
    created_by: str,
) -> dict:
    matter_id = "matter_" + uuid4().hex[:12]

    matter = {
        "matter_id": matter_id,
        "matter_name": matter_name,
        "client_name": client_name,
        "matter_type": matter_type,
        "status": status,
        "description": description,
        "primary_document": primary_document,
        "created_by": created_by,
        "created_at": utc_now_iso(),
    }

    try:
        inserted = supabase_insert(MATTERS_TABLE, matter)

        if inserted:
            return inserted
    except Exception as exc:
        print(f"[matters] Supabase matter insert failed: {exc}")

    DEMO_MATTERS[matter_id] = matter
    return matter


def assign_user_to_matter(
    user_email: str,
    matter_id: str,
    assigned_role: str,
    assigned_by: str,
) -> dict:
    matters_by_id = {
        matter["matter_id"]: matter
        for matter in list_all_matters()
    }

    if matter_id not in matters_by_id:
        raise ValueError("Matter does not exist.")

    for assignment in list_all_assignments():
        if (
            assignment["user_email"] == user_email
            and assignment["matter_id"] == matter_id
        ):
            return assignment

    assignment = {
        "assignment_id": "assign_" + uuid4().hex[:12],
        "user_email": user_email,
        "matter_id": matter_id,
        "assigned_role": assigned_role,
        "assigned_by": assigned_by,
        "assigned_at": utc_now_iso(),
    }

    try:
        inserted = supabase_insert(ASSIGNMENTS_TABLE, assignment)

        if inserted:
            return inserted
    except Exception as exc:
        print(f"[matters] Supabase assignment insert failed: {exc}")

    DEMO_MATTER_ASSIGNMENTS.append(assignment)
    return assignment


def remove_user_from_matter(user_email: str, matter_id: str) -> bool:
    try:
        deleted = supabase_delete(
            ASSIGNMENTS_TABLE,
            {
                "user_email": f"eq.{user_email}",
                "matter_id": f"eq.{matter_id}",
            },
        )

        if deleted:
            return True
    except Exception as exc:
        print(f"[matters] Supabase assignment delete failed: {exc}")

    original_count = len(DEMO_MATTER_ASSIGNMENTS)

    DEMO_MATTER_ASSIGNMENTS[:] = [
        assignment
        for assignment in DEMO_MATTER_ASSIGNMENTS
        if not (
            assignment["user_email"] == user_email
            and assignment["matter_id"] == matter_id
        )
    ]

    return len(DEMO_MATTER_ASSIGNMENTS) < original_count