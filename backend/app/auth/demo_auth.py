from fastapi import Header, HTTPException


DEMO_USERS = {
    "attorney@demo-law.com": {
        "firm_id": "firm_demo",
        "user_id": "user_attorney_ava",
        "user_email": "attorney@demo-law.com",
        "display_name": "Ava Johnson",
        "role": "Attorney",
        "allowed_matter_ids": [
            "matter_acme_smith",
            "matter_omega_contract",
        ],
    },
    "paralegal@demo-law.com": {
        "firm_id": "firm_demo",
        "user_id": "user_paralegal_ben",
        "user_email": "paralegal@demo-law.com",
        "display_name": "Ben Carter",
        "role": "Paralegal",
        "allowed_matter_ids": [
            "matter_acme_smith",
        ],
    },
    "admin@demo-law.com": {
        "firm_id": "firm_demo",
        "user_id": "user_admin_maria",
        "user_email": "admin@demo-law.com",
        "display_name": "Maria Lopez",
        "role": "Firm Admin",
        "allowed_matter_ids": [
            "*",
        ],
    },
}


def get_demo_user_by_email(user_email: str | None) -> dict:
    if not user_email:
        raise HTTPException(
            status_code=401,
            detail="Missing demo authentication header: X-Demo-User",
        )

    user = DEMO_USERS.get(user_email)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid demo user.",
        )

    return user


def get_demo_user(
    x_demo_user: str | None = Header(default=None),
) -> dict:
    """
    Demo authentication dependency.

    Frontend sends:
    X-Demo-User: attorney@demo-law.com
    """
    return get_demo_user_by_email(x_demo_user)


def authorize_matter_access(
    role: str,
    matter_id: str | None,
    allowed_matter_ids: list[str],
) -> bool:
    if role == "Firm Admin":
        return True

    if matter_id is None:
        return True

    return matter_id in allowed_matter_ids


def authorize_search_scope(role: str, search_scope: str) -> bool:
    allowed = {
        "Firm Admin": {
            "current_matter",
            "firm_knowledge_base",
            "ny_legal_authorities",
            "all_authorized_sources",
            "auto",
        },
        "Attorney": {
            "current_matter",
            "firm_knowledge_base",
            "ny_legal_authorities",
            "all_authorized_sources",
            "auto",
        },
        "Paralegal": {
            "current_matter",
            "firm_knowledge_base",
            "ny_legal_authorities",
            "all_authorized_sources",
            "auto",
        },
    }

    return search_scope in allowed.get(role, set())

def authorize_admin_access(role: str) -> bool:
    return role == "Firm Admin"


def list_demo_users() -> list[dict]:
    return [
        {
            "user_email": user["user_email"],
            "display_name": user["display_name"],
            "role": user["role"],
            "allowed_matter_ids": user["allowed_matter_ids"],
        }
        for user in DEMO_USERS.values()
    ]
def get_demo_permissions(role: str) -> dict:
    return {
        "can_use_all_sources": role in {"Attorney", "Firm Admin", "Paralegal"},
        "can_view_admin": role == "Firm Admin",
        "can_upload_documents": role in {"Attorney", "Paralegal", "Firm Admin"},
        "can_generate_drafts": role in {"Attorney", "Paralegal", "Firm Admin"},
        "can_extract_key_dates": role in {"Attorney", "Paralegal", "Firm Admin"},
        "can_assign_matters": role == "Firm Admin",
    }


def get_current_user_profile(user: dict) -> dict:
    return {
        **user,
        "permissions": get_demo_permissions(user["role"]),
    }