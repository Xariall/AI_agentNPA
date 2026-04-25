from collections import defaultdict

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from rank_bm25 import BM25Okapi

from app.config import settings
from app.core.embeddings import get_embedder

logger = structlog.get_logger()


class HybridRetriever:
    def __init__(self) -> None:
        self.qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        self.embedder = get_embedder()
        self._bm25_index: BM25Okapi | None = None
        self._bm25_corpus: list[dict] | None = None

    def build_bm25_index(self, chunks: list[dict]) -> None:
        """Build in-memory BM25 index from chunks."""
        tokenized = [c["metadata"]["raw_text"].lower().split() for c in chunks]
        self._bm25_index = BM25Okapi(tokenized)
        self._bm25_corpus = chunks
        logger.info("bm25_index_built", docs=len(chunks))

    def load_bm25_from_qdrant(self) -> None:
        """Load all points from Qdrant to build BM25 index."""
        all_points = []
        offset = None
        while True:
            result = self.qdrant.scroll(
                collection_name=settings.collection_name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            points, next_offset = result
            for p in points:
                all_points.append({
                    "id": str(p.id),
                    "text": p.payload.get("text", ""),
                    "metadata": {
                        k: v
                        for k, v in p.payload.items()
                        if k != "text"
                    },
                })
            if next_offset is None:
                break
            offset = next_offset

        if all_points:
            # For BM25 we use the raw_text from metadata
            tokenized = [p["metadata"].get("raw_text", p["text"]).lower().split() for p in all_points]
            self._bm25_index = BM25Okapi(tokenized)
            self._bm25_corpus = all_points
            logger.info("bm25_loaded_from_qdrant", docs=len(all_points))

    def _build_qdrant_filter(self, filters: dict | None) -> Filter | None:
        if not filters:
            return None
        conditions = []
        for key, value in filters.items():
            if isinstance(value, (str, int, bool)) and value:
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        if not conditions:
            return None
        return Filter(must=conditions)

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[dict]:
        """Hybrid search: dense (Qdrant) + sparse (BM25) with RRF fusion."""
        query_vec = self.embedder.embed_query(query)

        # Dense search via query_points (qdrant-client >= 1.17)
        dense_response = self.qdrant.query_points(
            collection_name=settings.collection_name,
            query=query_vec,
            query_filter=self._build_qdrant_filter(filters),
            limit=top_k * 2,
            with_payload=True,
        )

        dense_hits = [
            {
                "id": str(r.id),
                "text": r.payload.get("text", ""),
                "metadata": {k: v for k, v in r.payload.items() if k != "text"},
                "score": r.score,
            }
            for r in dense_response.points
        ]

        # BM25 search
        bm25_hits = []
        if self._bm25_index is not None and self._bm25_corpus is not None:
            tokenized_query = query.lower().split()
            bm25_scores = self._bm25_index.get_scores(tokenized_query)
            scored = list(zip(self._bm25_corpus, bm25_scores))
            scored.sort(key=lambda x: x[1], reverse=True)
            bm25_hits = [
                {**item, "score": float(score)}
                for item, score in scored[: top_k * 2]
                if score > 0
            ]

        # RRF fusion
        fused = _rrf_fusion(dense_hits, bm25_hits, k=60)
        logger.info(
            "hybrid_search",
            query=query[:80],
            dense=len(dense_hits),
            bm25=len(bm25_hits),
            fused=len(fused),
        )
        return fused[:top_k]


def _rrf_fusion(
    *result_lists: list[dict],
    k: int = 60,
) -> list[dict]:
    """Reciprocal Rank Fusion across multiple result lists."""
    scores: dict[str, float] = defaultdict(float)
    docs: dict[str, dict] = {}

    for results in result_lists:
        for rank, doc in enumerate(results):
            doc_id = doc["id"]
            scores[doc_id] += 1.0 / (k + rank + 1)
            if doc_id not in docs:
                docs[doc_id] = doc

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [{**docs[did], "score": scores[did]} for did in sorted_ids]


# Singleton
_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever
