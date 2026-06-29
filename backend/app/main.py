from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.agent.query_decomposer import decompose_queries
from app.auth.demo_auth import (
    authorize_admin_access,
    get_current_user_profile,
    get_demo_user,
    list_demo_users,
)
from app.config import settings
from app.documents.local_documents import (
    list_documents_for_matter,
    save_uploaded_text_document,
)
from app.governance.audit import list_audit_logs, list_security_events
from app.graph.pipeline import run_secure_agentic_rag_pipeline
from app.ingestion.local_index import build_local_chunks
from app.matters.demo_matters import (
    assign_user_to_matter,
    create_demo_matter,
    get_matter_for_user,
    list_all_assignments,
    list_all_matters,
    list_matters_for_user,
)
from app.retrieval.hybrid import hybrid_retrieve
from app.retrieval.reranker import rerank_chunks
from app.schemas import ChatRequest, ChatResponse


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Secure agentic RAG API for New York law firm matter intelligence.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }


@app.get("/auth/demo-users")
def get_demo_users():
    return {
        "items": list_demo_users(),
    }


@app.get("/auth/me")
def get_auth_me(user: dict = Depends(get_demo_user)):
    return get_current_user_profile(user)


@app.get("/matters")
def get_matters(user: dict = Depends(get_demo_user)):
    return {
        "items": list_matters_for_user(user),
    }


@app.get("/matters/{matter_id}")
def get_matter(matter_id: str, user: dict = Depends(get_demo_user)):
    matter = get_matter_for_user(user, matter_id)

    if matter is None:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this matter.",
        )

    return matter


@app.get("/documents")
def get_documents(
    matter_id: str,
    user: dict = Depends(get_demo_user),
):
    matter = get_matter_for_user(user, matter_id)

    if matter is None:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view documents for this matter.",
        )

    return {
        "items": list_documents_for_matter(matter_id),
    }


@app.post("/documents/upload")
async def upload_document(
    matter_id: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(get_demo_user),
):
    matter = get_matter_for_user(user, matter_id)

    if matter is None:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to upload documents to this matter.",
        )

    content = await file.read()

    try:
        document = save_uploaded_text_document(
            matter_id=matter_id,
            uploaded_by=user["user_email"],
            filename=file.filename or "uploaded_document.txt",
            content=content,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return document


@app.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    user: dict = Depends(get_demo_user),
):
    state = run_secure_agentic_rag_pipeline(
        query=request.query,
        matter_id=request.matter_id,
        search_scope=request.search_scope,
        user=user,
    )

    retrieval_methods = sorted(
        {
            chunk.get("retrieval_method")
            for chunk in state.get("reranked_chunks", [])
            if chunk.get("retrieval_method")
        }
    )

    response = {
        "answer": state.get("final_answer", ""),
        "citations": state.get("citations", []),
        "agent_plan": state.get("agent_plan"),
        "security": {
            "injection_label": state.get("injection_label", "UNKNOWN"),
            "input_pii_detected": state.get("input_pii_detected", False),
            "output_pii_detected": state.get("output_pii_detected", False),
            "relevance_score": state.get("top_relevance_score"),
            "evidence_status": state.get("evidence_status"),
            "faithfulness_score": state.get("faithfulness_score"),
            "hallucination_status": state.get("hallucination_status"),
            "final_status": state.get("final_status"),
        },
        "request_id": state.get("request_id"),
        "debug": {
            "requested_search_scope": state.get("requested_search_scope"),
            "resolved_search_scope": state.get("resolved_search_scope"),
            "retrieval_attempts": state.get("retrieval_attempts", 0),
            "redacted_query": state.get("redacted_query"),
            "private_queries": state.get("private_queries", []),
            "firm_kb_queries": state.get("firm_kb_queries", []),
            "ny_legal_queries": state.get("ny_legal_queries", []),
            "dense_results": len(state.get("dense_results", [])),
            "bm25_results": len(state.get("bm25_results", [])),
            "fused_results": len(state.get("fused_results", [])),
            "reranked_chunks": len(state.get("reranked_chunks", [])),
            "retrieval_methods": retrieval_methods,
            "top_chunks": state.get("reranked_chunks", [])[:5],
            "latency_ms": state.get("latency_ms"),
            "errors": state.get("errors", []),
        },
    }

    return response


@app.get("/debug/local-chunks")
def debug_local_chunks():
    chunks = build_local_chunks()

    return {
        "count": len(chunks),
        "items": chunks,
    }


@app.get("/debug/retrieve")
def debug_retrieve(
    query: str,
    matter_id: str | None = None,
    search_scope: str = "all_authorized_sources",
    user: dict = Depends(get_demo_user),
):
    if not get_matter_for_user(user, matter_id) and matter_id is not None:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this matter.",
        )

    source_map = {
        "current_matter": ["private_matter_docs"],
        "firm_knowledge_base": ["firm_knowledge_base"],
        "ny_legal_authorities": ["ny_legal_authorities"],
        "all_authorized_sources": [
            "private_matter_docs",
            "firm_knowledge_base",
            "ny_legal_authorities",
        ],
        "auto": [
            "private_matter_docs",
            "firm_knowledge_base",
            "ny_legal_authorities",
        ],
    }

    sources_needed = source_map.get(search_scope, source_map["all_authorized_sources"])

    query_pack = decompose_queries(
        raw_query=query,
        redacted_query=query,
        task_type="debug_retrieval",
    )

    retrieval = hybrid_retrieve(
        source_queries=query_pack,
        sources_needed=sources_needed,
        firm_id=user["firm_id"],
        matter_id=matter_id,
    )

    reranked = rerank_chunks(
        query=query,
        chunks=retrieval["fused_results"],
    )

    return {
        "query": query,
        "matter_id": matter_id,
        "search_scope": search_scope,
        "sources_needed": sources_needed,
        "dense_count": len(retrieval["dense_results"]),
        "bm25_count": len(retrieval["bm25_results"]),
        "fused_count": len(retrieval["fused_results"]),
        "reranked_count": len(reranked),
        "top_chunks": reranked[:5],
    }


@app.get("/admin/users")
def get_admin_users(user: dict = Depends(get_demo_user)):
    if not authorize_admin_access(user["role"]):
        raise HTTPException(
            status_code=403,
            detail="Only Firm Admin users can view users.",
        )

    return {
        "items": list_demo_users(),
    }


@app.get("/admin/matters")
def get_admin_matters(user: dict = Depends(get_demo_user)):
    if not authorize_admin_access(user["role"]):
        raise HTTPException(
            status_code=403,
            detail="Only Firm Admin users can view all matters.",
        )

    return {
        "items": list_all_matters(),
    }


@app.get("/admin/matter-assignments")
def get_admin_matter_assignments(user: dict = Depends(get_demo_user)):
    if not authorize_admin_access(user["role"]):
        raise HTTPException(
            status_code=403,
            detail="Only Firm Admin users can view matter assignments.",
        )

    return {
        "items": list_all_assignments(),
    }


@app.post("/admin/matters")
def create_admin_matter(payload: dict, user: dict = Depends(get_demo_user)):
    if not authorize_admin_access(user["role"]):
        raise HTTPException(
            status_code=403,
            detail="Only Firm Admin users can create matters.",
        )

    required_fields = [
        "matter_name",
        "client_name",
        "matter_type",
        "status",
        "description",
        "primary_document",
    ]

    missing_fields = [
        field for field in required_fields
        if not payload.get(field)
    ]

    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {', '.join(missing_fields)}",
        )

    matter = create_demo_matter(
        matter_name=payload["matter_name"],
        client_name=payload["client_name"],
        matter_type=payload["matter_type"],
        status=payload["status"],
        description=payload["description"],
        primary_document=payload["primary_document"],
        created_by=user["user_email"],
    )

    return matter


@app.post("/admin/matter-assignments")
def create_admin_matter_assignment(
    payload: dict,
    user: dict = Depends(get_demo_user),
):
    if not authorize_admin_access(user["role"]):
        raise HTTPException(
            status_code=403,
            detail="Only Firm Admin users can assign matters.",
        )

    user_email = payload.get("user_email")
    matter_id = payload.get("matter_id")
    assigned_role = payload.get("assigned_role", "Matter Team")

    if not user_email or not matter_id:
        raise HTTPException(
            status_code=400,
            detail="user_email and matter_id are required.",
        )

    try:
        assignment = assign_user_to_matter(
            user_email=user_email,
            matter_id=matter_id,
            assigned_role=assigned_role,
            assigned_by=user["user_email"],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return assignment


@app.get("/admin/audit-logs")
def get_audit_logs(user: dict = Depends(get_demo_user)):
    if not authorize_admin_access(user["role"]):
        raise HTTPException(
            status_code=403,
            detail="Only Firm Admin users can view audit logs.",
        )

    return {
        "items": list_audit_logs(),
    }


@app.get("/admin/security-events")
def get_security_events(user: dict = Depends(get_demo_user)):
    if not authorize_admin_access(user["role"]):
        raise HTTPException(
            status_code=403,
            detail="Only Firm Admin users can view security events.",
        )

    return {
        "items": list_security_events(),
    }