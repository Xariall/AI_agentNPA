import time

import structlog
from fastapi import APIRouter

from app.config import settings
from app.core.generation import generate_answer
from app.core.retrieval import get_retriever
from app.models.schemas import QueryRequest, QueryResponse, Source

logger = structlog.get_logger()
router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    start = time.time()

    retriever = get_retriever()
    filters = request.filters if request.filters else None
    chunks = retriever.search(
        query=request.question,
        top_k=request.top_k,
        filters=filters,
    )

    if not chunks or chunks[0]["score"] < settings.min_score_threshold:
        elapsed = (time.time() - start) * 1000
        return QueryResponse(
            answer="В предоставленных документах нет информации по этому вопросу.",
            sources=[],
            confidence="low",
            latency_ms=round(elapsed, 1),
        )

    answer = await generate_answer(request.question, chunks)

    sources = []
    for c in chunks[:5]:
        meta = c.get("metadata", {})
        sources.append(Source(
            doc_filename=meta.get("doc_filename", ""),
            doc_type=meta.get("doc_type", ""),
            doc_number=meta.get("doc_number", ""),
            chapter=meta.get("chapter", ""),
            article=meta.get("article", ""),
            paragraph=meta.get("paragraph", ""),
            score=round(c.get("score", 0.0), 4),
            text_preview=meta.get("raw_text", "")[:200],
        ))

    elapsed = (time.time() - start) * 1000
    confidence = _calculate_confidence(chunks)

    return QueryResponse(
        answer=answer,
        sources=sources,
        confidence=confidence,
        latency_ms=round(elapsed, 1),
    )


def _calculate_confidence(chunks: list[dict]) -> str:
    if not chunks:
        return "low"
    top_score = chunks[0].get("score", 0)
    if top_score > 0.02:
        return "high"
    if top_score > 0.015:
        return "medium"
    return "low"
