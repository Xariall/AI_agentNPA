from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api.routes import router
from app.core.retrieval import get_retriever

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load BM25 index from Qdrant on startup."""
    logger.info("startup", msg="Loading BM25 index from Qdrant...")
    try:
        retriever = get_retriever()
        retriever.load_bm25_from_qdrant()
        logger.info("startup_complete", msg="BM25 index loaded")
    except Exception:
        logger.exception("startup_error", msg="Failed to load BM25 index — BM25 search will be unavailable")
    yield


app = FastAPI(
    title="NPA Assistant",
    description="RAG-based assistant for Kazakhstan medical device regulations",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api")
