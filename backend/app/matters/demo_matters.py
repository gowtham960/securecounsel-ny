from datetime import datetime, timezone
from uuid import uuid4


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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def list_all_matters() -> list[dict]:
    return list(DEMO_MATTERS.values())


def list_all_assignments() -> list[dict]:
    return DEMO_MATTER_ASSIGNMENTS


def list_assigned_matter_ids_for_user(user_email: str) -> list[str]:
    return [
        assignment["matter_id"]
        for assignment in DEMO_MATTER_ASSIGNMENTS
        if assignment["user_email"] == user_email
    ]


def list_matters_for_user(user: dict) -> list[dict]:
    if user["role"] == "Firm Admin":
        return list_all_matters()

    assigned_matter_ids = set(list_assigned_matter_ids_for_user(user["user_email"]))

    return [
        matter
        for matter_id, matter in DEMO_MATTERS.items()
        if matter_id in assigned_matter_ids
    ]


def get_matter_for_user(user: dict, matter_id: str) -> dict | None:
    if user["role"] == "Firm Admin":
        return DEMO_MATTERS.get(matter_id)

    assigned_matter_ids = set(list_assigned_matter_ids_for_user(user["user_email"]))

    if matter_id not in assigned_matter_ids:
        return None

    return DEMO_MATTERS.get(matter_id)


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

    DEMO_MATTERS[matter_id] = matter
    return matter


def assign_user_to_matter(
    user_email: str,
    matter_id: str,
    assigned_role: str,
    assigned_by: str,
) -> dict:
    if matter_id not in DEMO_MATTERS:
        raise ValueError("Matter does not exist.")

    for assignment in DEMO_MATTER_ASSIGNMENTS:
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

    DEMO_MATTER_ASSIGNMENTS.append(assignment)
    return assignment


def remove_user_from_matter(user_email: str, matter_id: str) -> bool:
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