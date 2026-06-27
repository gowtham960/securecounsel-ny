import hashlib
import json
from datetime import datetime, timezone

from app.db.supabase_client import get_supabase_admin_client


IN_MEMORY_AUDIT_LOGS: list[dict] = []
IN_MEMORY_SECURITY_EVENTS: list[dict] = []


def hash_prompt(raw_prompt: str) -> str:
    return hashlib.sha256(raw_prompt.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_security_events(state: dict, audit_log_id: str) -> list[dict]:
    events = []

    if state.get("injection_label") == "INJECTION":
        events.append(
            {
                "event_type": "PROMPT_INJECTION_BLOCKED",
                "severity": "HIGH",
                "description": "A prompt injection attempt was blocked.",
            }
        )

    if state.get("final_status") in {"DENIED_BY_ROLE_POLICY", "DENIED_BY_SCOPE_POLICY"}:
        events.append(
            {
                "event_type": "UNAUTHORIZED_ACCESS_ATTEMPT",
                "severity": "HIGH",
                "description": "User attempted to access a restricted matter or scope.",
            }
        )

    if state.get("input_pii_detected"):
        events.append(
            {
                "event_type": "INPUT_PII_DETECTED",
                "severity": "MEDIUM",
                "description": "PII was detected in the user query.",
            }
        )

    if state.get("evidence_status") in {"WEAK", "NO_EVIDENCE"}:
        events.append(
            {
                "event_type": "WEAK_RETRIEVAL_EVIDENCE",
                "severity": "MEDIUM",
                "description": "Retrieved evidence was weak or missing.",
            }
        )

    if state.get("faithfulness_score", 1.0) < 0.85:
        events.append(
            {
                "event_type": "LOW_FAITHFULNESS",
                "severity": "HIGH",
                "description": "Generated answer failed faithfulness threshold.",
            }
        )

    records = []

    for event in events:
        records.append(
            {
                "created_at": _now_iso(),
                "firm_id": state.get("firm_id"),
                "user_id": state.get("user_id"),
                "user_email": state.get("user_email"),
                "role": state.get("role"),
                "matter_id": state.get("matter_id"),
                "event_type": event["event_type"],
                "severity": event["severity"],
                "description": event["description"],
                "related_audit_log_id": audit_log_id,
                "metadata": {
                    "request_id": state.get("request_id"),
                    "final_status": state.get("final_status"),
                    "injection_label": state.get("injection_label"),
                    "evidence_status": state.get("evidence_status"),
                    "faithfulness_score": state.get("faithfulness_score"),
                },
                "reviewed": False,
            }
        )

    return records


def build_audit_record(state: dict, audit_log_id: str) -> dict:
    return {
        "id": audit_log_id,
        "created_at": _now_iso(),

        "request_id": state.get("request_id"),
        "firm_id": state.get("firm_id"),
        "user_id": state.get("user_id"),
        "user_email": state.get("user_email"),
        "role": state.get("role"),

        "matter_id": state.get("matter_id"),
        "requested_search_scope": state.get("requested_search_scope"),
        "resolved_search_scope": state.get("resolved_search_scope"),

        "raw_prompt_hash": hash_prompt(state.get("raw_query", "")),
        "redacted_prompt": state.get("redacted_query"),

        "task_type": state.get("task_type"),
        "sources_needed": state.get("sources_needed"),

        "injection_label": state.get("injection_label"),
        "injection_reason": state.get("injection_reason"),
        "injection_risk_score": state.get("injection_risk_score"),

        "input_pii_detected": state.get("input_pii_detected"),
        "input_pii_entities": state.get("input_pii_entities"),

        "retrieved_private_document_ids": [
            chunk.get("document_id")
            for chunk in state.get("private_chunks", [])
        ],
        "retrieved_firm_kb_document_ids": [
            chunk.get("document_id")
            for chunk in state.get("firm_kb_chunks", [])
        ],
        "retrieved_legal_authorities": [
            chunk.get("citation")
            for chunk in state.get("legal_authority_chunks", [])
        ],

        "top_relevance_score": state.get("top_relevance_score"),
        "evidence_status": state.get("evidence_status"),
        "evidence_reason": state.get("evidence_reason"),

        "rerank_model": "stub-reranker",
        "generation_model": "groq-or-demo",

        "faithfulness_score": state.get("faithfulness_score"),
        "hallucination_status": state.get("hallucination_status"),

        "output_pii_detected": state.get("output_pii_detected"),
        "output_pii_entities": state.get("output_pii_entities"),
        "output_policy_status": state.get("output_policy_status"),

        "final_status": state.get("final_status"),
        "latency_ms": state.get("latency_ms"),
    }


def log_audit_event(state: dict) -> dict:
    audit_log_id = f"audit_{state.get('request_id')}"

    audit_record = build_audit_record(state, audit_log_id)
    security_events = build_security_events(state, audit_log_id)

    supabase = get_supabase_admin_client()

    if supabase is None:
        IN_MEMORY_AUDIT_LOGS.append(audit_record)
        IN_MEMORY_SECURITY_EVENTS.extend(security_events)

        print(json.dumps(audit_record, indent=2))
        return audit_record

    try:
        supabase.table("audit_logs").insert(audit_record).execute()

        if security_events:
            supabase.table("security_events").insert(security_events).execute()

        return audit_record

    except Exception as exc:
        fallback_record = {
            **audit_record,
            "supabase_logging_error": str(exc),
        }

        IN_MEMORY_AUDIT_LOGS.append(fallback_record)
        IN_MEMORY_SECURITY_EVENTS.extend(security_events)

        print(json.dumps(fallback_record, indent=2))
        return fallback_record


def list_audit_logs() -> list[dict]:
    supabase = get_supabase_admin_client()

    if supabase is None:
        return list(reversed(IN_MEMORY_AUDIT_LOGS))

    try:
        response = (
            supabase.table("audit_logs")
            .select("*")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        return response.data or []
    except Exception:
        return list(reversed(IN_MEMORY_AUDIT_LOGS))


def list_security_events() -> list[dict]:
    supabase = get_supabase_admin_client()

    if supabase is None:
        return list(reversed(IN_MEMORY_SECURITY_EVENTS))

    try:
        response = (
            supabase.table("security_events")
            .select("*")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        return response.data or []
    except Exception:
        return list(reversed(IN_MEMORY_SECURITY_EVENTS))