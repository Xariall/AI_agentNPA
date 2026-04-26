from typing import Literal

from pydantic import BaseModel


class ExpectedSource(BaseModel):
    doc_filename: str
    article: str | None = None


class EvalItem(BaseModel):
    id: str
    question: str
    expected_answer_keywords: list[str] = []
    expected_sources: list[ExpectedSource] = []
    doc_type_filter: str | None = None
    difficulty: Literal["easy", "medium", "hard"]
    category: str
    should_refuse: bool = False
