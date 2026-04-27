"""
Eval runner: run all questions through the RAG pipeline and compute metrics.

Usage:
    cd /Users/asanaliesmagambetov/Documents/AI_agentNPA/backend
    uv run python eval/runner.py baseline
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from statistics import mean, median

import yaml

# backend/ is the root — add it to path so `app` and `eval` are importable
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from app.graph.rag_graph import build_graph
from eval.metrics import (
    compute_hit_rate,
    compute_keyword_coverage,
    compute_mrr,
    compute_refusal_correctness,
    compute_verification_failure_rate,
)
from eval.schemas import EvalItem

DATASET_PATH = Path(__file__).resolve().parent / "dataset.yaml"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


async def run_single(graph, item: EvalItem) -> dict:
    start = time.perf_counter()

    state = await graph.ainvoke({
        "question": item.question,
        "filters": {"doc_type": item.doc_type_filter} if item.doc_type_filter else None,
    })

    latency_ms = (time.perf_counter() - start) * 1000

    return {
        "id": item.id,
        "question": item.question,
        "expected_sources": [s.model_dump() for s in item.expected_sources],
        "expected_keywords": item.expected_answer_keywords,
        "should_refuse": item.should_refuse,
        "category": item.category,
        "difficulty": item.difficulty,
        "answer": state.get("answer", ""),
        "retrieved_sources": state.get("sources", []),
        "refused": state.get("refused", False),
        "confidence": state.get("confidence", "low"),
        "verification_failed": state.get("verification_failed", False),
        "latency_ms": latency_ms,
    }


def _group_by(results: list[dict], key: str) -> dict:
    groups: dict[str, list] = {}
    for r in results:
        groups.setdefault(r[key], []).append(r)
    return {
        k: {
            "count": len(v),
            "keyword_coverage": compute_keyword_coverage(v),
            "refusal_correctness": compute_refusal_correctness(v),
        }
        for k, v in groups.items()
    }


async def main(tag: str = "baseline"):
    with open(DATASET_PATH, encoding="utf-8") as f:
        items = [EvalItem(**x) for x in yaml.safe_load(f)]

    print(f"Running eval on {len(items)} questions...")

    graph = build_graph()
    results = []
    for item in items:
        print(f"  [{item.id}] {item.question[:60]}...")
        try:
            result = await run_single(graph, item)
            results.append(result)
        except Exception as e:
            print(f"    ERROR: {e}")
            results.append({
                "id": item.id,
                "question": item.question,
                "expected_sources": [s.model_dump() for s in item.expected_sources],
                "expected_keywords": item.expected_answer_keywords,
                "should_refuse": item.should_refuse,
                "category": item.category,
                "difficulty": item.difficulty,
                "answer": f"ERROR: {e}",
                "retrieved_sources": [],
                "refused": False,
                "confidence": "error",
                "verification_failed": False,
                "latency_ms": 0,
            })

    latencies = [r["latency_ms"] for r in results if r["latency_ms"] > 0]
    sorted_latencies = sorted(latencies) if latencies else [0]

    metrics = {
        "retrieval": {
            "hit_rate@1": compute_hit_rate(results, k=1),
            "hit_rate@3": compute_hit_rate(results, k=3),
            "hit_rate@5": compute_hit_rate(results, k=5),
            "mrr": compute_mrr(results),
        },
        "generation": {
            "keyword_coverage": compute_keyword_coverage(results),
            "refusal_correctness": compute_refusal_correctness(results),
            "verification_failure_rate": compute_verification_failure_rate(results),
        },
        "performance": {
            "latency_p50": median(latencies) if latencies else 0,
            "latency_p95": sorted_latencies[int(len(sorted_latencies) * 0.95)] if latencies else 0,
            "latency_mean": mean(latencies) if latencies else 0,
        },
        "by_category": _group_by(results, "category"),
        "by_difficulty": _group_by(results, "difficulty"),
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"{tag}_{timestamp}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"metrics": metrics, "results": results}, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to {output_path}")
    print(f"\nKey metrics:")
    print(f"  Hit Rate @ 1: {metrics['retrieval']['hit_rate@1']:.1%}")
    print(f"  Hit Rate @ 5: {metrics['retrieval']['hit_rate@5']:.1%}")
    print(f"  MRR: {metrics['retrieval']['mrr']:.3f}")
    print(f"  Keyword Coverage: {metrics['generation']['keyword_coverage']:.1%}")
    print(f"  Refusal Correctness: {metrics['generation']['refusal_correctness']:.1%}")
    print(f"  Verification Failure Rate: {metrics['generation']['verification_failure_rate']:.1%}")
    print(f"  Latency p50: {metrics['performance']['latency_p50']:.0f}ms")
    print(f"  Latency p95: {metrics['performance']['latency_p95']:.0f}ms")

    return metrics


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "run"
    asyncio.run(main(tag))
