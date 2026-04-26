from __future__ import annotations

from typing import TypedDict

import structlog
from langgraph.graph import END, StateGraph

from app.core.generation import generate_answer
from app.core.reranker import rerank
from app.core.retrieval import get_retriever
from app.core.verification import verify_citations

logger = structlog.get_logger()

# CrossEncoder raw logits: need higher threshold to reject out-of-scope queries
# baseline showed 4/6 out-of-scope were incorrectly answered
RERANK_SCORE_THRESHOLD = 1.5
MIN_CHUNKS_FOR_ANSWER = 1

ABBREVIATIONS = {
    "МИ": "медицинские изделия",
    "НМИРК": "Номенклатура медицинских изделий Республики Казахстан",
    "НПА": "нормативный правовой акт",
    "РК": "Республика Казахстан",
    "ЕАЭС": "Евразийский экономический союз",
    "МЗ": "Министерство здравоохранения",
    "ДСМ": "Департамент санитарного мониторинга",
}


class RAGState(TypedDict, total=False):
    question: str
    filters: dict | None
    rewritten_query: str
    retrieved_chunks: list[dict]
    reranked_chunks: list[dict]
    confidence: str
    answer: str
    sources: list[dict]
    refused: bool
    verification_failed: bool


def query_rewriter_node(state: RAGState) -> dict:
    """Expand abbreviations: МИ -> медицинские изделия, etc."""
    rewritten = state["question"]
    for abbr, full in ABBREVIATIONS.items():
        padded = f" {rewritten} "
        if f" {abbr} " in padded or f" {abbr}." in padded or f" {abbr}?" in padded:
            rewritten = rewritten.replace(abbr, f"{abbr} ({full})")

    logger.info("query_rewritten", original=state["question"][:80], rewritten=rewritten[:80])
    return {"rewritten_query": rewritten}


def retrieval_node(state: RAGState) -> dict:
    """Retrieve chunks from Qdrant using dense search."""
    retriever = get_retriever()
    filters = state.get("filters")
    if filters and not any(filters.values()):
        filters = None

    chunks = retriever.search(
        query=state["rewritten_query"],
        top_k=30,
        filters=filters,
    )
    return {"retrieved_chunks": chunks}


def rerank_node(state: RAGState) -> dict:
    """Rerank retrieved chunks using cross-encoder."""
    reranked = rerank(state["rewritten_query"], state["retrieved_chunks"], top_k=5)
    return {"reranked_chunks": reranked}


def confidence_node(state: RAGState) -> dict:
    """Decide whether to answer or refuse based on rerank scores."""
    chunks = state.get("reranked_chunks", [])

    if not chunks or len(chunks) < MIN_CHUNKS_FOR_ANSWER:
        return {"confidence": "low", "refused": True}

    top_score = chunks[0].get("rerank_score", 0)
    if top_score < RERANK_SCORE_THRESHOLD:
        return {"confidence": "low", "refused": True}

    # CrossEncoder logits: >2 strong, >0 moderate, <0 weak
    if top_score > 2.0:
        confidence = "high"
    elif top_score > 0.0:
        confidence = "medium"
    else:
        confidence = "low"

    return {"confidence": confidence, "refused": False}


def route_after_confidence(state: RAGState) -> str:
    return "refuse" if state.get("refused") else "generate"


async def generate_node(state: RAGState) -> dict:
    """Generate answer using Gemini with reranked chunks."""
    chunks = state["reranked_chunks"]
    answer = await generate_answer(state["question"], chunks)

    sources = []
    for c in chunks:
        meta = c.get("metadata", {})
        sources.append({
            "doc_filename": meta.get("doc_filename", ""),
            "doc_type": meta.get("doc_type", ""),
            "doc_number": meta.get("doc_number", ""),
            "article": meta.get("article", ""),
            "paragraph": meta.get("paragraph", ""),
            "score": round(c.get("rerank_score", 0), 4),
            "text_preview": meta.get("raw_text", "")[:200],
        })

    return {"answer": answer, "sources": sources}


def verify_node(state: RAGState) -> dict:
    """Check for hallucinated citations in the answer."""
    failed = verify_citations(state["answer"], state.get("reranked_chunks", []))
    return {"verification_failed": failed}


def refuse_node(state: RAGState) -> dict:
    """Return refusal response."""
    return {
        "answer": "В предоставленных документах нет информации по этому вопросу.",
        "sources": [],
        "confidence": "low",
        "verification_failed": False,
    }


def build_graph() -> StateGraph:
    """Build and compile the RAG LangGraph."""
    g = StateGraph(RAGState)

    g.add_node("rewrite", query_rewriter_node)
    g.add_node("retrieve", retrieval_node)
    g.add_node("rerank", rerank_node)
    g.add_node("check_confidence", confidence_node)
    g.add_node("generate", generate_node)
    g.add_node("verify", verify_node)
    g.add_node("refuse", refuse_node)

    g.set_entry_point("rewrite")
    g.add_edge("rewrite", "retrieve")
    g.add_edge("retrieve", "rerank")
    g.add_edge("rerank", "check_confidence")

    g.add_conditional_edges(
        "check_confidence",
        route_after_confidence,
        {"generate": "generate", "refuse": "refuse"},
    )

    g.add_edge("generate", "verify")
    g.add_edge("verify", END)
    g.add_edge("refuse", END)

    return g.compile()
