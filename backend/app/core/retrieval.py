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
        all_points: list[dict] = []
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

    def _bm25_search(
        self,
        query: str,
        top_k: int,
    ) -> list[dict]:
        """Sparse BM25 search over the full in-memory corpus."""
        if self._bm25_index is None or self._bm25_corpus is None:
            return []

        tokenized_query = query.lower().split()
        scores = self._bm25_index.get_scores(tokenized_query)

        scored: list[tuple[float, int]] = [
            (float(score), idx)
            for idx, score in enumerate(scores)
            if score > 0
        ]
        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "id": self._bm25_corpus[idx]["id"],
                "text": self._bm25_corpus[idx]["text"],
                "metadata": self._bm25_corpus[idx]["metadata"],
                "score": score,
            }
            for score, idx in scored[:top_k]
        ]

    @staticmethod
    def _rrf_fuse(
        dense_hits: list[dict],
        sparse_hits: list[dict],
        k: int = 60,
        top_k: int = 20,
    ) -> list[dict]:
        """Reciprocal Rank Fusion of two ranked lists."""
        rrf_scores: dict[str, float] = {}
        doc_map: dict[str, dict] = {}

        for rank, hit in enumerate(dense_hits):
            doc_id = hit["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
            doc_map[doc_id] = hit

        for rank, hit in enumerate(sparse_hits):
            doc_id = hit["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
            if doc_id not in doc_map:
                doc_map[doc_id] = hit

        sorted_ids = sorted(rrf_scores, key=lambda d: rrf_scores[d], reverse=True)
        results = []
        for doc_id in sorted_ids[:top_k]:
            hit = doc_map[doc_id]
            results.append({**hit, "rrf_score": rrf_scores[doc_id]})
        return results

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[dict]:
        """Hybrid search: dense (Qdrant) + sparse (BM25) with RRF fusion."""
        query_vec = self.embedder.embed_query(query)

        # Dense search via Qdrant
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

        # BM25 sparse search — full corpus, no domain filter (reranker handles relevance)
        bm25_hits = self._bm25_search(query, top_k=top_k * 2)

        if bm25_hits:
            # Fuse dense + sparse via RRF
            fused = self._rrf_fuse(dense_hits, bm25_hits, k=settings.rrf_k, top_k=top_k)
            logger.info(
                "hybrid_search",
                query=query[:80],
                dense=len(dense_hits),
                bm25=len(bm25_hits),
                fused=len(fused),
            )
            return fused

        # Fallback: dense-only if BM25 unavailable
        logger.info("dense_search", query=query[:80], hits=len(dense_hits))
        return dense_hits[:top_k]


# Singleton
_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever
