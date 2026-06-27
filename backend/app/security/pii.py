import re


def redact_pii(text: str) -> dict:
    """
    MVP redactor.
    Later this becomes Microsoft Presidio.
    """
    pii_detected = False
    entities = []

    patterns = {
        "EMAIL_ADDRESS": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "US_SSN": r"\b\d{3}-\d{2}-\d{4}\b",
        "PHONE_NUMBER": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    }

    redacted = text

    for entity_type, pattern in patterns.items():
        matches = list(re.finditer(pattern, redacted))

        if matches:
            pii_detected = True

        for match in matches:
            entities.append(
                {
                    "entity_type": entity_type,
                    "text": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                }
            )

        redacted = re.sub(pattern, f"<{entity_type}>", redacted)

    return {
        "text": redacted,
        "pii_detected": pii_detected,
        "entities": entities,
    }