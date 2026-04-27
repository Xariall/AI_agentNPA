from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""
    embedding_model: str = "intfloat/multilingual-e5-large"
    collection_name: str = "npa"
    data_dir: str = "./data"
    min_score_threshold: float = 0.3
    top_k: int = 10
    # LLM backend: "ollama" | "gemini"
    llm_backend: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    # RAG pipeline tuning
    retrieval_top_k: int = 50
    rerank_top_n: int = 20
    # BGE reranker outputs 0-1 (sigmoid); mmarco outputs raw logits — adjust accordingly
    rerank_score_threshold: float = 0.05
    rrf_k: int = 60
    # Set ENABLE_RERANKING=false to skip cross-encoder (saves ~120MB RAM on memory-constrained deployments)
    enable_reranking: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
