def reciprocal_rank_fusion(
    dense_results: list[dict],
    bm25_results: list[dict],
    k: int = 60,
) -> list[dict]:
    fused: dict[str, dict] = {}

    for rank, item in enumerate(dense_results, start=1):
        chunk_id = item["chunk_id"]
        if chunk_id not in fused:
            fused[chunk_id] = dict(item)
            fused[chunk_id]["fusion_score"] = 0.0

        fused[chunk_id]["fusion_score"] += 1 / (k + rank)

    for rank, item in enumerate(bm25_results, start=1):
        chunk_id = item["chunk_id"]
        if chunk_id not in fused:
            fused[chunk_id] = dict(item)
            fused[chunk_id]["fusion_score"] = 0.0

        fused[chunk_id]["fusion_score"] += 1 / (k + rank)

    results = list(fused.values())

    for item in results:
        item["score"] = max(item.get("score", 0.0), item.get("fusion_score", 0.0))

    return sorted(results, key=lambda item: item.get("fusion_score", 0.0), reverse=True)