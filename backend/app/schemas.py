from typing import Any, Literal
from pydantic import BaseModel, Field


SearchScope = Literal[
    "current_matter",
    "firm_knowledge_base",
    "ny_legal_authorities",
    "all_authorized_sources",
    "auto",
]


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    matter_id: str | None = None
    search_scope: SearchScope = "auto"


class Citation(BaseModel):
    collection: str
    document_id: str
    chunk_id: str
    citation: str | None = None
    score: float | None = None


class AgentPlan(BaseModel):
    task_type: str
    sources_needed: list[str]
    reason: str
    steps: list[str]


class SecurityMetadata(BaseModel):
    injection_label: str
    input_pii_detected: bool
    output_pii_detected: bool
    relevance_score: float | None = None
    evidence_status: str | None = None
    faithfulness_score: float | None = None
    hallucination_status: str | None = None
    final_status: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = []
    agent_plan: AgentPlan | None = None
    security: SecurityMetadata
    request_id: str
    debug: dict[str, Any] | None = None