from statistics import mean


def compute_hit_rate(results: list[dict], k: int) -> float:
    """Fraction of questions where the correct document is in top-k retrieved sources."""
    hits = 0
    counted = 0
    for r in results:
        if r["should_refuse"] or not r["expected_sources"]:
            continue
        counted += 1
        expected_files = {s["doc_filename"] for s in r["expected_sources"]}
        retrieved_files = {s["doc_filename"] for s in r["retrieved_sources"][:k]}
        if expected_files & retrieved_files:
            hits += 1
    return hits / counted if counted else 0.0


def compute_mrr(results: list[dict]) -> float:
    """Mean Reciprocal Rank of the correct source."""
    reciprocal_ranks = []
    for r in results:
        if r["should_refuse"] or not r["expected_sources"]:
            continue
        expected_files = {s["doc_filename"] for s in r["expected_sources"]}
        rank = None
        for i, src in enumerate(r["retrieved_sources"], start=1):
            if src["doc_filename"] in expected_files:
                rank = i
                break
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
    return mean(reciprocal_ranks) if reciprocal_ranks else 0.0


def compute_keyword_coverage(results: list[dict]) -> float:
    """Fraction of expected keywords present in the answer."""
    coverages = []
    for r in results:
        if r["should_refuse"] or not r["expected_keywords"]:
            continue
        answer_lower = r["answer"].lower()
        present = sum(1 for kw in r["expected_keywords"] if kw.lower() in answer_lower)
        coverages.append(present / len(r["expected_keywords"]))
    return mean(coverages) if coverages else 0.0


def compute_refusal_correctness(results: list[dict]) -> float:
    """Fraction of questions where the system correctly answered or refused."""
    correct = 0
    for r in results:
        if r["should_refuse"] and r["refused"]:
            correct += 1
        elif not r["should_refuse"] and not r["refused"]:
            correct += 1
    return correct / len(results) if results else 0.0


def compute_verification_failure_rate(results: list[dict]) -> float:
    """Fraction of non-refused answers with hallucinated citations."""
    eligible = [r for r in results if not r["refused"]]
    if not eligible:
        return 0.0
    failures = sum(1 for r in eligible if r.get("verification_failed", False))
    return failures / len(eligible)
