import re
import time
import uuid
from collections import defaultdict

from app.agent.evidence_grader import grade_evidence
from app.agent.planner import plan_legal_task
from app.agent.query_decomposer import decompose_queries
from app.agent.query_rewriter import rewrite_query_for_retry
from app.auth.demo_auth import (
    authorize_matter_access,
    authorize_search_scope,
)
from app.config import settings
from app.evaluation.faithfulness import check_faithfulness
from app.generation.groq_llm import generate_answer
from app.governance.audit import log_audit_event
from app.graph.state import SecureAgentState
from app.retrieval.hybrid import hybrid_retrieve
from app.retrieval.reranker import rerank_chunks
from app.security.injection import classify_prompt_injection
from app.security.pii import redact_pii


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9\-]+", text.lower()))


def _query_intent_terms(query: str) -> dict:
    lowered = query.lower()

    payment_terms = {
        "payment",
        "payments",
        "invoice",
        "invoices",
        "due",
        "paid",
        "pay",
        "payable",
        "receipt",
        "net",
        "net 30",
        "thirty days",
        "30 days",
        "schedule",
    }

    termination_terms = {
        "termination",
        "terminate",
        "notice",
        "cause",
        "end",
        "ending",
    }

    confidentiality_terms = {
        "confidential",
        "confidentiality",
        "disclose",
        "disclosure",
        "proprietary",
        "pricing",
        "customer lists",
    }

    restrictive_covenant_terms = {
        "non-solicitation",
        "non solicitation",
        "non-compete",
        "non compete",
        "restrictive covenant",
        "solicit",
        "clients",
    }

    return {
        "payment": any(term in lowered for term in payment_terms),
        "termination": any(term in lowered for term in termination_terms),
        "confidentiality": any(term in lowered for term in confidentiality_terms),
        "restrictive_covenant": any(
            term in lowered for term in restrictive_covenant_terms
        ),
    }


def _chunk_matches_query_intent(query: str, chunk: dict) -> bool:
    text = chunk.get("text", "").lower()
    query_lower = query.lower()
    intent = _query_intent_terms(query)

    if intent["payment"]:
        has_payment_language = any(
            term in text
            for term in [
                "payment",
                "payments",
                "invoice",
                "invoices",
                "due",
                "receipt",
                "net 30",
                "thirty days",
                "30 days",
                "pay invoices",
                "amount",
            ]
        )

        has_payment_answer_language = any(
            term in text
            for term in [
                "invoice",
                "invoices",
                "due",
                "receipt",
                "net 30",
                "thirty days",
                "30 days",
                "pay invoices",
            ]
        )

        return has_payment_language and has_payment_answer_language

    if intent["termination"]:
        return any(
            term in text
            for term in [
                "termination",
                "terminate",
                "notice",
                "cause",
                "thirty days written notice",
            ]
        )

    if intent["confidentiality"]:
        return any(
            term in text
            for term in [
                "confidential",
                "confidentiality",
                "disclose",
                "proprietary",
                "pricing",
                "customer lists",
            ]
        )

    if intent["restrictive_covenant"]:
        return any(
            term in text
            for term in [
                "non-solicitation",
                "non solicitation",
                "non-compete",
                "non compete",
                "restrictive covenant",
                "solicit",
            ]
        )

    query_tokens = _tokenize(query_lower)
    chunk_tokens = _tokenize(text)

    if not query_tokens or not chunk_tokens:
        return False

    overlap = query_tokens.intersection(chunk_tokens)
    return len(overlap) >= 2


def _score_chunk_for_evidence_selection(query: str, chunk: dict) -> float:
    base_score = float(chunk.get("score") or 0.0)
    text = chunk.get("text", "").lower()
    source_type = chunk.get("source_type") or ""
    collection = chunk.get("collection") or ""
    intent = _query_intent_terms(query)

    bonus = 0.0

    if collection == "uploaded_matter_docs":
        bonus += 0.08

    if source_type in {
        "uploaded_csv",
        "uploaded_xlsx",
        "uploaded_pdf",
        "uploaded_docx",
        "uploaded_txt",
    }:
        bonus += 0.05

    if intent["payment"]:
        if "invoice" in text or "invoices" in text:
            bonus += 0.18
        if "due" in text:
            bonus += 0.10
        if "payment" in text or "payments" in text:
            bonus += 0.10
        if "receipt" in text or "net 30" in text or "thirty days" in text:
            bonus += 0.10
        if source_type in {"uploaded_csv", "uploaded_xlsx"}:
            bonus += 0.12

    if intent["termination"]:
        if "termination" in text or "terminate" in text:
            bonus += 0.15
        if "notice" in text:
            bonus += 0.08

    if intent["confidentiality"]:
        if "confidential" in text or "confidentiality" in text:
            bonus += 0.15
        if "disclose" in text or "proprietary" in text:
            bonus += 0.08

    if intent["restrictive_covenant"]:
        if "non-solicitation" in text or "solicit" in text:
            bonus += 0.15
        if "non-compete" in text or "restrictive covenant" in text:
            bonus += 0.10

    return round(base_score + bonus, 4)


def select_evidence_chunks(
    query: str,
    reranked_chunks: list[dict],
    limit: int = 4,
) -> list[dict]:
    if not reranked_chunks:
        return []

    scored_candidates = []

    for chunk in reranked_chunks:
        if not _chunk_matches_query_intent(query, chunk):
            continue

        evidence_score = _score_chunk_for_evidence_selection(query, chunk)
        scored_candidates.append(
            {
                **chunk,
                "evidence_selection_score": evidence_score,
            }
        )

    if not scored_candidates:
        scored_candidates = [
            {
                **chunk,
                "evidence_selection_score": _score_chunk_for_evidence_selection(
                    query, chunk
                ),
            }
            for chunk in reranked_chunks[:limit]
        ]

    scored_candidates = sorted(
        scored_candidates,
        key=lambda item: item.get("evidence_selection_score", 0.0),
        reverse=True,
    )

    top_score = scored_candidates[0].get("evidence_selection_score", 0.0) or 0.0
    min_score = max(0.25, top_score * 0.72)

    filtered = [
        chunk
        for chunk in scored_candidates
        if (chunk.get("evidence_selection_score", 0.0) or 0.0) >= min_score
    ]

    if not filtered:
        filtered = scored_candidates[:1]

    selected_by_document = defaultdict(list)

    for chunk in filtered:
        selected_by_document[chunk.get("document_id")].append(chunk)

    best_document_id = None
    best_document_score = -1.0

    for document_id, chunks in selected_by_document.items():
        document_score = max(
            chunk.get("evidence_selection_score", 0.0) or 0.0 for chunk in chunks
        )

        if document_score > best_document_score:
            best_document_id = document_id
            best_document_score = document_score

    primary_document_chunks = [
        chunk for chunk in filtered if chunk.get("document_id") == best_document_id
    ]

    secondary_chunks = [
        chunk for chunk in filtered if chunk.get("document_id") != best_document_id
    ]

    selected = primary_document_chunks + secondary_chunks

    seen = set()
    deduped = []

    for chunk in selected:
        key = (chunk.get("document_id"), chunk.get("chunk_id"))

        if key in seen:
            continue

        seen.add(key)
        deduped.append(chunk)

        if len(deduped) >= limit:
            break

    return deduped


def build_clean_citations(selected_chunks: list[dict], limit: int = 4) -> list[dict]:
    citations = []
    seen = set()

    for chunk in selected_chunks:
        key = (chunk.get("document_id"), chunk.get("chunk_id"))

        if key in seen:
            continue

        seen.add(key)

        citations.append(
            {
                "collection": chunk.get("collection"),
                "document_id": chunk.get("document_id"),
                "chunk_id": chunk.get("chunk_id"),
                "citation": chunk.get("citation"),
                "score": chunk.get("score"),
                "source_type": chunk.get("source_type"),
                "evidence_selection_score": chunk.get("evidence_selection_score"),
            }
        )

        if len(citations) >= limit:
            break

    return citations


def build_selected_documents(selected_chunks: list[dict]) -> list[dict]:
    documents = {}

    for chunk in selected_chunks:
        document_id = chunk.get("document_id")

        if not document_id:
            continue

        current = documents.get(document_id)

        if current is None:
            documents[document_id] = {
                "document_id": document_id,
                "title": chunk.get("title"),
                "citation": chunk.get("citation"),
                "collection": chunk.get("collection"),
                "source_type": chunk.get("source_type"),
                "highest_score": chunk.get("score"),
                "highest_evidence_selection_score": chunk.get(
                    "evidence_selection_score"
                ),
                "selected_chunk_ids": [chunk.get("chunk_id")],
            }
        else:
            current["selected_chunk_ids"].append(chunk.get("chunk_id"))

            if (chunk.get("score") or 0.0) > (current.get("highest_score") or 0.0):
                current["highest_score"] = chunk.get("score")

            if (chunk.get("evidence_selection_score") or 0.0) > (
                current.get("highest_evidence_selection_score") or 0.0
            ):
                current["highest_evidence_selection_score"] = chunk.get(
                    "evidence_selection_score"
                )

    return list(documents.values())


def run_secure_agentic_rag_pipeline(
    query: str,
    matter_id: str | None,
    search_scope: str,
    user: dict | None = None,
) -> SecureAgentState:
    started = time.time()

    state: SecureAgentState = {
        "request_id": str(uuid.uuid4()),
        "raw_query": query,
        "matter_id": matter_id,
        "requested_search_scope": search_scope,
        "retrieval_attempts": 0,
        "errors": [],
        "final_status": "STARTED",
    }

    try:
        if user is None:
            raise ValueError("Authenticated user is required.")

        state["firm_id"] = user["firm_id"]
        state["user_id"] = user["user_id"]
        state["user_email"] = user["user_email"]
        state["role"] = user["role"]
        state["allowed_matter_ids"] = user["allowed_matter_ids"]

        if not authorize_search_scope(state["role"], search_scope):
            state["final_status"] = "DENIED_BY_SCOPE_POLICY"
            state["final_answer"] = "Access denied for this search scope."
            state["latency_ms"] = int((time.time() - started) * 1000)
            log_audit_event(state)
            return state

        if not authorize_matter_access(
            role=state["role"],
            matter_id=matter_id,
            allowed_matter_ids=state["allowed_matter_ids"],
        ):
            state["final_status"] = "DENIED_BY_ROLE_POLICY"
            state["final_answer"] = "Access denied for this matter."
            state["latency_ms"] = int((time.time() - started) * 1000)
            log_audit_event(state)
            return state

        injection = classify_prompt_injection(query)
        state["injection_label"] = injection["label"]
        state["injection_reason"] = injection["reason"]
        state["injection_risk_score"] = injection["risk_score"]

        if injection["label"] == "INJECTION":
            state["final_status"] = "BLOCKED_PROMPT_INJECTION"
            state["final_answer"] = "Your request was blocked by the security policy."
            state["latency_ms"] = int((time.time() - started) * 1000)
            log_audit_event(state)
            return state

        input_pii = redact_pii(query)
        state["redacted_query"] = input_pii["text"]
        state["input_pii_detected"] = input_pii["pii_detected"]
        state["input_pii_entities"] = input_pii["entities"]

        plan = plan_legal_task(
            raw_query=query,
            requested_search_scope=search_scope,
            matter_id=matter_id,
        )
        state["agent_plan"] = plan
        state["task_type"] = plan["task_type"]
        state["sources_needed"] = plan["sources_needed"]
        state["resolved_search_scope"] = (
            "all_authorized_sources"
            if len(plan["sources_needed"]) > 1
            else plan["sources_needed"][0]
        )

        query_pack = decompose_queries(
            raw_query=query,
            redacted_query=state["redacted_query"],
            task_type=state["task_type"],
        )
        state["private_queries"] = query_pack["private_queries"]
        state["firm_kb_queries"] = query_pack["firm_kb_queries"]
        state["ny_legal_queries"] = query_pack["ny_legal_queries"]

        max_retrieval_attempts = 3
        best_reranked = []
        best_evidence = {
            "status": "NO_EVIDENCE",
            "reason": "No retrieval attempts completed.",
            "top_score": None,
        }
        best_query_pack = query_pack

        for attempt in range(1, max_retrieval_attempts + 1):
            if attempt == 1:
                attempt_query = state["redacted_query"]
            else:
                attempt_query = rewrite_query_for_retry(
                    original_query=state["redacted_query"],
                    search_scope=search_scope,
                    attempt=attempt,
                    sources_needed=state["sources_needed"],
                )

            attempt_query_pack = decompose_queries(
                raw_query=attempt_query,
                redacted_query=attempt_query,
                task_type=state["task_type"],
            )

            retrieval = hybrid_retrieve(
                source_queries=attempt_query_pack,
                sources_needed=state["sources_needed"],
                firm_id=state["firm_id"],
                matter_id=matter_id,
            )

            reranked = rerank_chunks(
                query=attempt_query,
                chunks=retrieval["fused_results"],
            )

            evidence = grade_evidence(reranked)
            state["retrieval_attempts"] += 1

            current_top = evidence["top_score"] or 0
            best_top = best_evidence["top_score"] or 0

            if current_top > best_top:
                best_reranked = reranked
                best_evidence = evidence
                best_query_pack = attempt_query_pack

                state["dense_results"] = retrieval["dense_results"]
                state["bm25_results"] = retrieval["bm25_results"]
                state["fused_results"] = retrieval["fused_results"]
                state["reranked_chunks"] = reranked
                state["private_queries"] = attempt_query_pack["private_queries"]
                state["firm_kb_queries"] = attempt_query_pack["firm_kb_queries"]
                state["ny_legal_queries"] = attempt_query_pack["ny_legal_queries"]

            if evidence["status"] == "STRONG":
                break

        reranked = best_reranked
        evidence = best_evidence
        query_pack = best_query_pack

        selected_evidence_chunks = select_evidence_chunks(
            query=state["redacted_query"],
            reranked_chunks=reranked,
            limit=4,
        )

        if selected_evidence_chunks:
            generation_chunks = selected_evidence_chunks
        else:
            generation_chunks = reranked[:4]

        state["selected_evidence_chunks"] = selected_evidence_chunks
        state["selected_documents"] = build_selected_documents(generation_chunks)

        state["private_chunks"] = [
            chunk
            for chunk in generation_chunks
            if chunk.get("collection") == "private_matter_docs"
        ]
        state["uploaded_matter_chunks"] = [
            chunk
            for chunk in generation_chunks
            if chunk.get("collection") == "uploaded_matter_docs"
        ]
        state["firm_kb_chunks"] = [
            chunk
            for chunk in generation_chunks
            if chunk.get("collection") == "firm_knowledge_base"
        ]
        state["legal_authority_chunks"] = [
            chunk
            for chunk in generation_chunks
            if chunk.get("collection") == "ny_legal_authorities"
        ]

        state["evidence_status"] = evidence["status"]
        state["evidence_reason"] = evidence["reason"]
        state["top_relevance_score"] = evidence["top_score"]

        if evidence["status"] == "NO_EVIDENCE":
            state["final_status"] = "NO_EVIDENCE"
            state["final_answer"] = (
                "I could not find enough support in the authorized sources to answer safely."
            )
            state["latency_ms"] = int((time.time() - started) * 1000)
            log_audit_event(state)
            return state

        if evidence["status"] == "WEAK":
            state["final_status"] = "WEAK_EVIDENCE"
            state["final_answer"] = (
                "I tried multiple retrieval strategies, but the evidence is still too weak "
                "to provide a reliable answer. Please narrow the question, choose All Authorized Sources, "
                "or select a more specific matter/document."
            )
            state["latency_ms"] = int((time.time() - started) * 1000)
            log_audit_event(state)
            return state

        answer = generate_answer(
            redacted_query=state["redacted_query"],
            chunks=generation_chunks,
            agent_plan=plan,
        )
        state["generated_answer"] = answer

        contexts = [chunk["text"] for chunk in generation_chunks]
        faithfulness = check_faithfulness(
            question=state["redacted_query"],
            answer=answer,
            contexts=contexts,
        )
        state["faithfulness_score"] = faithfulness["score"]
        state["hallucination_status"] = faithfulness["status"]

        if state["faithfulness_score"] < settings.faithfulness_threshold:
            state["final_status"] = "LOW_FAITHFULNESS"
            state["final_answer"] = (
                "The system found potentially relevant sources, but the generated answer "
                "did not pass the faithfulness threshold."
            )
            state["latency_ms"] = int((time.time() - started) * 1000)
            log_audit_event(state)
            return state

        output_pii = redact_pii(answer)
        state["final_answer"] = output_pii["text"]
        state["output_pii_detected"] = output_pii["pii_detected"]
        state["output_pii_entities"] = output_pii["entities"]
        state["output_policy_status"] = "ALLOW"

        state["citations"] = build_clean_citations(generation_chunks, limit=4)

        state["final_status"] = "SUCCESS"
        state["latency_ms"] = int((time.time() - started) * 1000)
        log_audit_event(state)

        return state

    except Exception as exc:
        state["final_status"] = "ERROR"
        state["errors"].append(str(exc))
        state["final_answer"] = "An internal error occurred while processing the request."
        state["latency_ms"] = int((time.time() - started) * 1000)
        log_audit_event(state)
        return state