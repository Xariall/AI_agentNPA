import structlog
from google import genai

from app.config import settings
from app.prompts.system import SYSTEM_PROMPT

logger = structlog.get_logger()


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def format_chunks_for_prompt(chunks: list[dict]) -> str:
    """Format retrieved chunks into numbered context blocks."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source_info = []
        if meta.get("doc_filename"):
            source_info.append(meta["doc_filename"])
        if meta.get("article"):
            source_info.append(f"Статья {meta['article']}")
        if meta.get("paragraph"):
            source_info.append(f"п. {meta['paragraph']}")

        source_label = ", ".join(source_info) if source_info else f"Фрагмент {i}"
        text = meta.get("raw_text", chunk.get("text", ""))
        parts.append(f"[{i}] {source_label}\n{text}")

    return "\n\n---\n\n".join(parts)


async def generate_answer(query: str, chunks: list[dict]) -> str:
    """Generate answer using Gemini with retrieved context."""
    context = format_chunks_for_prompt(chunks)

    client = _get_client()
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"<context>\n{context}\n</context>\n\nВопрос: {query}",
        config={
            "system_instruction": SYSTEM_PROMPT,
            "temperature": 0.1,
        },
    )

    answer = response.text or "Не удалось сгенерировать ответ."
    logger.info("generated_answer", query=query[:80], answer_len=len(answer))
    return answer
