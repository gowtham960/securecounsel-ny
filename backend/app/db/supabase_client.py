from supabase import Client, create_client

from app.config import settings


def get_supabase_admin_client() -> Client | None:
    """
    Returns a Supabase admin client if environment variables are configured.

    MVP behavior:
    - If Supabase keys are missing, return None.
    - Governance logging will fall back to in-memory logs.
    """
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None

    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )