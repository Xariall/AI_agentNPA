import structlog
from sentence_transformers import CrossEncoder

logger = structlog.get_logger()

RERANKER_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"

_reranker: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        logger.info("loading_reranker", model=RERANKER_MODEL)
        _reranker = CrossEncoder(RERANKER_MODEL)
        logger.info("reranker_loaded")
    return _reranker


def rerank(query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    """Rerank chunks by cross-encoder relevance score."""
    if not chunks:
        return []

    reranker = get_reranker()

    pairs = [[query, c.get("metadata", {}).get("raw_text", c.get("text", ""))] for c in chunks]
    scores = reranker.predict(pairs)

    scored_chunks = []
    for chunk, score in zip(chunks, scores):
        scored_chunks.append({**chunk, "rerank_score": float(score)})

    scored_chunks.sort(key=lambda c: c["rerank_score"], reverse=True)
    top_score = scored_chunks[0]["rerank_score"] if scored_chunks else 0
    logger.info("reranked", total=len(chunks), top_k=top_k, top_score=round(top_score, 4))
    return scored_chunks[:top_k]
