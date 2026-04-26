import asyncio
import json
import time
from pathlib import Path

import structlog
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.graph.rag_graph import build_graph
from app.models.schemas import QueryRequest, QueryResponse, Source

logger = structlog.get_logger()
router = APIRouter()

_graph = None

EVAL_RESULTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "eval" / "results"


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    start = time.time()

    graph = get_graph()
    state = await graph.ainvoke({
        "question": request.question,
        "filters": request.filters if request.filters else None,
    })

    elapsed = (time.time() - start) * 1000

    sources = []
    for s in state.get("sources", []):
        sources.append(Source(
            doc_filename=s.get("doc_filename", ""),
            doc_type=s.get("doc_type", ""),
            doc_number=s.get("doc_number", ""),
            chapter=s.get("chapter", ""),
            article=s.get("article", ""),
            paragraph=s.get("paragraph", ""),
            score=round(s.get("score", 0.0), 4),
            text_preview=s.get("text_preview", ""),
        ))

    return QueryResponse(
        answer=state.get("answer", "Ошибка генерации ответа."),
        sources=sources,
        confidence=state.get("confidence", "low"),
        latency_ms=round(elapsed, 1),
        verification_failed=state.get("verification_failed", False),
    )


@router.post("/query/stream")
async def query_stream(request: QueryRequest):
    async def event_generator():
        start = time.time()

        yield {
            "event": "status",
            "data": json.dumps({"stage": "retrieval", "message": "Поиск релевантных НПА..."}),
        }

        graph = get_graph()
        state = await graph.ainvoke({
            "question": request.question,
            "filters": request.filters if request.filters else None,
        })

        elapsed = (time.time() - start) * 1000

        sources = []
        for s in state.get("sources", []):
            sources.append({
                "doc_filename": s.get("doc_filename", ""),
                "doc_type": s.get("doc_type", ""),
                "doc_number": s.get("doc_number", ""),
                "article": s.get("article", ""),
                "paragraph": s.get("paragraph", ""),
                "score": round(s.get("score", 0.0), 4),
                "text_preview": s.get("text_preview", ""),
            })

        yield {
            "event": "sources",
            "data": json.dumps({
                "sources": sources,
                "confidence": state.get("confidence", "low"),
                "verification_failed": state.get("verification_failed", False),
                "refused": state.get("refused", False),
            }),
        }

        answer = state.get("answer", "")
        chunk_size = 8
        for i in range(0, len(answer), chunk_size):
            chunk = answer[i:i + chunk_size]
            yield {"event": "token", "data": json.dumps({"token": chunk})}
            await asyncio.sleep(0.015)

        yield {
            "event": "done",
            "data": json.dumps({"latency_ms": round(elapsed, 1)}),
        }

    return EventSourceResponse(event_generator())


@router.get("/eval/latest")
async def eval_latest():
    """Return the most recent eval run metrics."""
    if not EVAL_RESULTS_DIR.exists():
        return {"error": "No eval results found"}

    result_files = sorted(EVAL_RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not result_files:
        return {"error": "No eval results found"}

    latest = result_files[0]
    with open(latest, encoding="utf-8") as f:
        data = json.load(f)

    metrics = data.get("metrics", {})
    results = data.get("results", [])

    return {
        "filename": latest.name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M", time.localtime(latest.stat().st_mtime)),
        "eval_set_size": len(results),
        "metrics": metrics,
    }


@router.get("/eval/history")
async def eval_history():
    """Return metrics for all eval runs (for iteration chart)."""
    if not EVAL_RESULTS_DIR.exists():
        return []

    runs = []
    for f in sorted(EVAL_RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime):
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
        m = data.get("metrics", {})
        runs.append({
            "tag": f.stem,
            "timestamp": time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime)),
            "hit_rate_5": m.get("retrieval", {}).get("hit_rate@5", 0),
            "mrr": m.get("retrieval", {}).get("mrr", 0),
            "keyword_coverage": m.get("generation", {}).get("keyword_coverage", 0),
            "refusal_correctness": m.get("generation", {}).get("refusal_correctness", 0),
            "verification_failure_rate": m.get("generation", {}).get("verification_failure_rate", 0),
            "latency_p95": m.get("performance", {}).get("latency_p95", 0),
        })
    return runs
