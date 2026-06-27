def plan_legal_task(
    raw_query: str,
    requested_search_scope: str,
    matter_id: str | None,
) -> dict:
    """
    MVP rule-based planner.
    Later this can become an LLM planner.
    """
    lowered = raw_query.lower()

    task_type = "legal_research"
    sources_needed = []

    if requested_search_scope != "auto":
        if requested_search_scope == "current_matter":
            sources_needed = ["private_matter_docs"]
        elif requested_search_scope == "firm_knowledge_base":
            sources_needed = ["firm_knowledge_base"]
        elif requested_search_scope == "ny_legal_authorities":
            sources_needed = ["ny_legal_authorities"]
        elif requested_search_scope == "all_authorized_sources":
            sources_needed = [
                "private_matter_docs",
                "firm_knowledge_base",
                "ny_legal_authorities",
            ]
    else:
        if any(
            term in lowered
            for term in ["contract", "agreement", "clause", "non-compete", "termination"]
        ):
            task_type = "contract_review"

        if any(term in lowered for term in ["cplr", "statute", "law", "new york", "ny"]):
            sources_needed.append("ny_legal_authorities")

        if matter_id is not None or any(
            term in lowered for term in ["client", "matter", "contract", "agreement", "john smith"]
        ):
            sources_needed.append("private_matter_docs")

        if any(term in lowered for term in ["playbook", "template", "firm", "checklist", "standard"]):
            sources_needed.append("firm_knowledge_base")

        if not sources_needed:
            sources_needed = ["ny_legal_authorities"]

        if task_type == "contract_review" and "firm_knowledge_base" not in sources_needed:
            sources_needed.append("firm_knowledge_base")

    sources_needed = list(dict.fromkeys(sources_needed))

    steps = [
        "Classify the legal task.",
        "Select authorized sources.",
        "Create source-specific search queries.",
        "Run hybrid retrieval using vector search and BM25.",
        "Fuse and rerank results.",
        "Grade evidence strength.",
        "Generate a grounded answer.",
        "Run faithfulness and output safety checks.",
        "Log governance metadata.",
    ]

    return {
        "task_type": task_type,
        "sources_needed": sources_needed,
        "reason": "Planner selected sources based on query terms, matter context, and requested search scope.",
        "steps": steps,
    }