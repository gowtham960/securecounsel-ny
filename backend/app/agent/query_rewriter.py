def rewrite_query_for_retry(
    original_query: str,
    search_scope: str,
    attempt: int,
    sources_needed: list[str] | None = None,
) -> str:
    """
    Rule-based query rewriting for retrieval retry attempts.

    Attempt 1 is handled by the original query outside this function.
    This function is used for attempt 2 and attempt 3.

    Later, this can be replaced with an LLM-powered query rewriting step.
    """
    query = original_query.strip()
    lowered = query.lower()
    sources_needed = sources_needed or []

    if attempt <= 1:
        return query

    # Restrictive covenant / employment agreement review.
    if "restrictive covenant" in lowered:
        if search_scope == "firm_knowledge_base":
            return (
                "restrictive covenant playbook review factors checklist "
                "legitimate business interest duration geographic scope "
                "employee role client relationships confidential information "
                "narrow tailoring enforceability"
            )

        if search_scope == "ny_legal_authorities":
            return (
                "New York restrictive covenant employment enforceability "
                "non-compete non-solicitation legitimate business interest "
                "duration geographic scope narrow tailoring"
            )

        return (
            "restrictive covenant review factors legitimate business interest "
            "duration geographic scope employee role client relationships "
            "confidential information narrow tailoring"
        )

    # Non-solicitation questions.
    if "non-solicitation" in lowered or "nonsolicitation" in lowered:
        if search_scope == "firm_knowledge_base":
            return (
                "non-solicitation restrictive covenant review factors "
                "client solicitation material contact customer relationships "
                "duration legitimate business interest"
            )

        if search_scope == "ny_legal_authorities":
            return (
                "New York non-solicitation employment restriction "
                "client solicitation enforceability legitimate business interest"
            )

        return (
            "non-solicitation clause client solicitation material contact "
            "post-employment restriction duration customer relationships"
        )

    # Non-compete questions.
    if "non-compete" in lowered or "noncompete" in lowered:
        if search_scope == "firm_knowledge_base":
            return (
                "non-compete restrictive covenant review factors duration "
                "geographic scope employee role legitimate business interest "
                "narrow tailoring"
            )

        if search_scope == "ny_legal_authorities":
            return (
                "New York non-compete employment restriction enforceability "
                "duration geographic scope legitimate business interest"
            )

        return (
            "non-compete employment restriction duration geographic scope "
            "legitimate business interest narrow tailoring"
        )

    # Confidentiality questions.
    if "confidential" in lowered or "confidentiality" in lowered:
        return (
            "confidentiality clause confidential information trade secrets "
            "client lists pricing business information disclosure restriction"
        )

    # Termination questions.
    if "termination" in lowered or "terminate" in lowered:
        return (
            "termination clause notice period immediate termination cause "
            "employment agreement written notice"
        )

    # General firm KB fallback.
    if search_scope == "firm_knowledge_base":
        return (
            f"{query} firm playbook legal review checklist risk factors "
            "attorney review practical considerations"
        )

    # General NY authority fallback.
    if search_scope == "ny_legal_authorities":
        return (
            f"{query} New York statute employment law legal authority "
            "enforceability requirements"
        )

    # General fallback for all/current matter.
    return (
        f"{query} agreement clause provision legal review risk factors "
        "relevant document evidence"
    )