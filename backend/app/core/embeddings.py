import structlog
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = structlog.get_logger()


class E5Embedder:
    def __init__(self) -> None:
        logger.info("loading_embedding_model", model=settings.embedding_model)
        self.model = SentenceTransformer(settings.embedding_model)
        self.dimension = self.model.get_embedding_dimension()
        logger.info("embedding_model_loaded", dimension=self.dimension)

    def embed_documents(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Embed documents with 'passage: ' prefix required by E5."""
        prefixed = [f"passage: {t}" for t in texts]
        embeddings = self.model.encode(
            prefixed,
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=True,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed a query with 'query: ' prefix required by E5."""
        embedding = self.model.encode(
            f"query: {text}",
            normalize_embeddings=True,
        )
        return embedding.tolist()


# Singleton — loaded once on first import at startup
_embedder: E5Embedder | None = None


def get_embedder() -> E5Embedder:
    global _embedder
    if _embedder is None:
        _embedder = E5Embedder()
    return _embedder
