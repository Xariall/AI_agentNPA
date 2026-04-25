from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    embedding_model: str = "intfloat/multilingual-e5-large"
    collection_name: str = "npa"
    data_dir: str = "./data"
    min_score_threshold: float = 0.3
    top_k: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
