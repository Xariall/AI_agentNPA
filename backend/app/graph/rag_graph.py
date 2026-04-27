from __future__ import annotations

import asyncio
from typing import TypedDict

import structlog
from langgraph.graph import END, StateGraph

from app.config import settings
from app.core.generation import generate_answer, generate_hypothetical_doc, generate_query_variants
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
    "СМК": "система менеджмента качества",
    "ИВД": "изделия для диагностики in vitro",
    "ГОСТ": "государственный стандарт",
    "ТУ": "технические условия",
    "КР": "Кыргызская Республика",
    "РУ": "регистрационное удостоверение",
}


class RAGState(TypedDict, total=False):
    question: str
    filters: dict | None
    domain: str | None
    rewritten_query: str
    query_variants: list[str]
    hypothetical_doc: str
    retrieved_chunks: list[dict]
    reranked_chunks: list[dict]
    confidence: str
    answer: str
    sources: list[dict]
    refused: bool
    verification_failed: bool


def query_rewriter_node(state: RAGState) -> dict:
    """Expand abbreviations to full terms for better embedding and BM25 matching.

    Uses full replacement (not parenthetical) to avoid polluting the embedding
    with the abbreviated form alongside the full form.
    """
    import re
    rewritten = state["question"]
    for abbr, full in ABBREVIATIONS.items():
        # Match abbreviation as a whole word (not inside another word)
        rewritten = re.sub(rf"\b{re.escape(abbr)}\b", full, rewritten)

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


async def multi_query_node(state: RAGState) -> dict:
    """Generate query variants and a HyDE passage in parallel for broader retrieval coverage."""
    variants_task = generate_query_variants(state["rewritten_query"])
    hyde_task = generate_hypothetical_doc(state["rewritten_query"])
    variants, hypothetical_doc = await asyncio.gather(variants_task, hyde_task)
    return {"query_variants": variants, "hypothetical_doc": hypothetical_doc}


def retrieval_node(state: RAGState) -> dict:
    """Retrieve chunks using multi-query hybrid search (dense + BM25 + RRF)."""
    retriever = get_retriever()
    filters = state.get("filters")
    if filters and not any(filters.values()):
        filters = None

    # All queries: original + variants
    all_queries = [state["rewritten_query"]] + (state.get("query_variants") or [])

    chunks = retriever.multi_search(
        queries=all_queries,
        top_k=settings.retrieval_top_k,
        filters=filters,
        hypothetical_doc=state.get("hypothetical_doc", ""),
    )
    return {"retrieved_chunks": chunks}


def rerank_node(state: RAGState) -> dict:
    """Rerank retrieved chunks using cross-encoder (if enabled)."""
    if not settings.enable_reranking:
        # Skip cross-encoder; pass through top-N chunks with a dummy score above threshold
        chunks = state["retrieved_chunks"][:settings.rerank_top_n]
        scored = [{**c, "rerank_score": 2.0} for c in chunks]
        return {"reranked_chunks": scored}
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

    # BGE reranker: 0-1 sigmoid scale (>0.7 strong, >0.3 moderate, <0.3 weak)
    if top_score > 0.7:
        confidence = "high"
    elif top_score > 0.3:
        confidence = "medium"
    else:
        confidence = "low"

    return {"confidence": confidence, "refused": False}


def route_after_confidence(state: RAGState) -> str:
    return "refuse" if state.get("refused") else "generate"


async def generate_node(state: RAGState) -> dict:
    """Generate answer using LLM with reranked chunks.

    Deduplicates by doc_filename so the top-5 sources cover 5 distinct
    documents. The reranker may return multiple chunks from the same document;
    we keep the first (highest-ranked) chunk per document.
    """
    all_chunks = state["reranked_chunks"]

    # Deduplicate by doc_filename — keep highest-ranked chunk per document
    seen_files: set[str] = set()
    unique_chunks: list[dict] = []
    for c in all_chunks:
        fname = c.get("metadata", {}).get("doc_filename", "")
        if fname not in seen_files:
            seen_files.add(fname)
            unique_chunks.append(c)

    top_chunks = unique_chunks[:5]
    answer = await generate_answer(state["question"], top_chunks)

    sources = []
    for c in top_chunks:
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
    all_chunks = state.get("reranked_chunks", [])
    seen: set[str] = set()
    unique_chunks: list[dict] = []
    for c in all_chunks:
        fname = c.get("metadata", {}).get("doc_filename", "")
        if fname not in seen:
            seen.add(fname)
            unique_chunks.append(c)
    failed = verify_citations(state["answer"], unique_chunks[:5])
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
    g.add_node("multi_query", multi_query_node)
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
        {"retrieve": "multi_query", "refuse": "refuse"},
    )

    g.add_edge("multi_query", "retrieve")
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
