def decompose_queries(
    raw_query: str,
    redacted_query: str,
    task_type: str,
) -> dict:
    """
    Creates source-specific query variants.
    """
    private_queries = [
        raw_query,
    ]

    firm_kb_queries = [
        redacted_query,
    ]

    ny_legal_queries = [
        redacted_query,
    ]

    lowered = raw_query.lower()

    if "non-compete" in lowered or "noncompete" in lowered:
        private_queries.append("non-compete restrictive covenant employment agreement")
        firm_kb_queries.append("restrictive covenant non-compete enforceability review")
        ny_legal_queries.append("New York non-compete employment restrictive covenant enforceability")

    if "termination" in lowered:
        private_queries.append("termination clause breach cure notice agreement")
        firm_kb_queries.append("termination clause review playbook breach cure notice")
        ny_legal_queries.append("New York contract termination breach cure notice")

    if "cplr 3211" in lowered:
        ny_legal_queries.append("CPLR 3211 motion to dismiss failure to state cause of action")

    return {
        "private_queries": private_queries,
        "firm_kb_queries": firm_kb_queries,
        "ny_legal_queries": ny_legal_queries,
    }