import asyncio
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api.routes import router
from app.core.reranker import get_reranker
from app.core.retrieval import get_retriever

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load BM25 index from Qdrant on startup (deferred to background)."""
    logger.info("startup", msg=f"App starting on port {os.getenv('PORT', '8000')}...")
    # Load BM25 in background so health check is immediately available
    asyncio.create_task(_load_bm25())
    yield


async def _load_bm25():
    """Load BM25 index and pre-warm reranker in the background after startup."""
    await asyncio.sleep(5)  # Give uvicorn a moment to bind
    logger.info("bm25_load_start", msg="Loading BM25 index from Qdrant...")
    try:
        retriever = get_retriever()
        retriever.load_bm25_from_qdrant()
        logger.info("bm25_load_complete", msg="BM25 index loaded")
    except Exception:
        logger.exception("bm25_load_error", msg="Failed to load BM25 index — BM25 search will be unavailable")
    # Pre-warm the reranker so it's in RAM before the first request arrives
    try:
        get_reranker()
        logger.info("reranker_prewarm_complete")
    except Exception:
        logger.exception("reranker_prewarm_error", msg="Failed to pre-warm reranker")


app = FastAPI(
    title="NPA Assistant",
    description="RAG-based assistant for Kazakhstan medical device regulations",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api")


@app.post("/eval/run")
async def run_eval(tag: str = "api_run"):
    """Run evaluation pipeline and return metrics."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from eval.runner import main as eval_main

    metrics = await eval_main(tag)
    return {"status": "ok", "metrics": metrics}
