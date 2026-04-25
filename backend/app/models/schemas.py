from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    top_k: int = 10
    filters: dict | None = None


class Source(BaseModel):
    doc_filename: str
    doc_type: str = ""
    doc_number: str = ""
    chapter: str = ""
    article: str = ""
    paragraph: str = ""
    score: float = 0.0
    text_preview: str = ""


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
    confidence: str = "medium"
    latency_ms: float = 0.0


class ChunkData(BaseModel):
    id: str
    text: str
    metadata: dict
