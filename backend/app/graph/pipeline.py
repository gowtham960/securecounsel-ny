import time
import uuid

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

        state["private_chunks"] = [
            chunk
            for chunk in reranked
            if chunk.get("collection") == "private_matter_docs"
        ]
        state["firm_kb_chunks"] = [
            chunk
            for chunk in reranked
            if chunk.get("collection") == "firm_knowledge_base"
        ]
        state["legal_authority_chunks"] = [
            chunk
            for chunk in reranked
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
            chunks=reranked[:6],
            agent_plan=plan,
        )
        state["generated_answer"] = answer

        contexts = [chunk["text"] for chunk in reranked[:6]]
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

        state["citations"] = [
            {
                "collection": chunk.get("collection"),
                "document_id": chunk.get("document_id"),
                "chunk_id": chunk.get("chunk_id"),
                "citation": chunk.get("citation"),
                "score": chunk.get("score"),
            }
            for chunk in reranked[:6]
        ]

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