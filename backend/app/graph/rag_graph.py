from __future__ import annotations

from typing import TypedDict

import structlog
from langgraph.graph import END, StateGraph

from app.config import settings
from app.core.generation import generate_answer
from app.core.query_classifier import classify_query_domain
from app.core.reranker import rerank
from app.core.retrieval import get_retriever
from app.core.verification import verify_citations

logger = structlog.get_logger()

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
    domain: str | None
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


def classify_domain_node(state: RAGState) -> dict:
    """Classify query domain. Refuse medicine queries; pass all others to retrieval.

    Note: we intentionally do NOT add a domain= filter to the retrieval step.
    Metadata domain tagging in the corpus is imperfect (mixed-domain docs,
    cross-references), so the reranker is a more reliable relevance gate.
    The classifier's only job here is to reject clearly out-of-domain queries.
    """
    query = state["rewritten_query"]
    domain = classify_query_domain(query)

    if domain == "medicine":
        logger.info("domain_classified", domain=domain, action="refuse")
        return {"domain": domain, "refused": True}

    logger.info("domain_classified", domain=domain or "none")
    return {"domain": domain, "refused": False}


def route_after_classify(state: RAGState) -> str:
    return "refuse" if state.get("refused") else "retrieve"


def retrieval_node(state: RAGState) -> dict:
    """Retrieve chunks using hybrid search (dense + BM25 + RRF)."""
    retriever = get_retriever()
    filters = state.get("filters")
    if filters and not any(filters.values()):
        filters = None

    chunks = retriever.search(
        query=state["rewritten_query"],
        top_k=settings.retrieval_top_k,
        filters=filters,
    )
    return {"retrieved_chunks": chunks}


def rerank_node(state: RAGState) -> dict:
    """Rerank retrieved chunks using cross-encoder."""
    reranked = rerank(state["rewritten_query"], state["retrieved_chunks"], top_k=settings.rerank_top_n)
    return {"reranked_chunks": reranked}


def confidence_node(state: RAGState) -> dict:
    """Decide whether to answer or refuse based on rerank scores."""
    chunks = state.get("reranked_chunks", [])

    if not chunks or len(chunks) < MIN_CHUNKS_FOR_ANSWER:
        return {"confidence": "low", "refused": True}

    top_score = chunks[0].get("rerank_score", 0)
    if top_score < settings.rerank_score_threshold:
        return {"confidence": "low", "refused": True}

    # CrossEncoder logits: >3 strong, >1 moderate, <1 weak
    if top_score > 3.0:
        confidence = "high"
    elif top_score > 1.0:
        confidence = "medium"
    else:
        confidence = "low"

    return {"confidence": confidence, "refused": False}


def route_after_confidence(state: RAGState) -> str:
    return "refuse" if state.get("refused") else "generate"


async def generate_node(state: RAGState) -> dict:
    """Generate answer using LLM with reranked chunks."""
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
    g.add_node("classify_domain", classify_domain_node)
    g.add_node("retrieve", retrieval_node)
    g.add_node("rerank", rerank_node)
    g.add_node("check_confidence", confidence_node)
    g.add_node("generate", generate_node)
    g.add_node("verify", verify_node)
    g.add_node("refuse", refuse_node)

    g.set_entry_point("rewrite")
    g.add_edge("rewrite", "classify_domain")

    g.add_conditional_edges(
        "classify_domain",
        route_after_classify,
        {"retrieve": "retrieve", "refuse": "refuse"},
    )

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
