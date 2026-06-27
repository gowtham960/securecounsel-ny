from typing import Any, TypedDict


class SecureAgentState(TypedDict, total=False):
    request_id: str
    session_id: str | None

    raw_query: str
    redacted_query: str

    firm_id: str
    user_id: str
    user_email: str
    role: str

    matter_id: str | None
    allowed_matter_ids: list[str]
    requested_search_scope: str
    resolved_search_scope: str

    injection_label: str
    injection_reason: str
    injection_risk_score: int

    input_pii_detected: bool
    input_pii_entities: list[dict[str, Any]]

    task_type: str
    agent_plan: dict[str, Any]
    sources_needed: list[str]

    private_queries: list[str]
    firm_kb_queries: list[str]
    ny_legal_queries: list[str]

    dense_results: list[dict[str, Any]]
    bm25_results: list[dict[str, Any]]
    fused_results: list[dict[str, Any]]
    reranked_chunks: list[dict[str, Any]]

    private_chunks: list[dict[str, Any]]
    firm_kb_chunks: list[dict[str, Any]]
    legal_authority_chunks: list[dict[str, Any]]

    top_relevance_score: float
    evidence_status: str
    evidence_reason: str
    retrieval_attempts: int

    generated_answer: str

    faithfulness_score: float
    hallucination_status: str

    output_pii_detected: bool
    output_pii_entities: list[dict[str, Any]]
    output_policy_status: str

    final_answer: str
    citations: list[dict[str, Any]]

    final_status: str
    errors: list[str]

    latency_ms: int