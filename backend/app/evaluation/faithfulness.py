def check_faithfulness(
    question: str,
    answer: str,
    contexts: list[str],
) -> dict:
    """
    MVP stub.
    Later this becomes RAGAS faithfulness.
    """
    if not contexts:
        return {
            "score": 0.0,
            "status": "UNFAITHFUL",
        }

    return {
        "score": 0.91,
        "status": "FAITHFUL",
    }