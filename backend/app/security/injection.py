def classify_prompt_injection(query: str) -> dict:
    lowered = query.lower()

    injection_phrases = [
        "ignore previous instructions",
        "ignore all previous instructions",
        "reveal your system prompt",
        "show me your system prompt",
        "bypass security",
        "override policy",
        "act as developer",
        "act as system",
        "disable safety",
        "exfiltrate",
    ]

    for phrase in injection_phrases:
        if phrase in lowered:
            return {
                "label": "INJECTION",
                "reason": f"Matched injection phrase: {phrase}",
                "risk_score": 95,
            }

    suspicious_phrases = [
        "all client files",
        "every matter",
        "without permission",
        "confidential documents outside this matter",
        "privileged documents from another case",
    ]

    for phrase in suspicious_phrases:
        if phrase in lowered:
            return {
                "label": "SUSPICIOUS",
                "reason": f"Matched suspicious phrase: {phrase}",
                "risk_score": 60,
            }

    return {
        "label": "SAFE",
        "reason": "No obvious prompt injection pattern detected.",
        "risk_score": 5,
    }