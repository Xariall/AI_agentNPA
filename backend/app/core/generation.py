import asyncio

import httpx
import structlog
from google import genai
from google.genai import errors as genai_errors

from app.config import settings
from app.prompts.system import SYSTEM_PROMPT

logger = structlog.get_logger()

GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
MAX_RETRIES = 3
RETRY_DELAY = 2.0


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


async def _generate_ollama(query: str, context: str) -> str:
    """Generate answer using local Ollama model."""
    url = f"{settings.ollama_base_url}/api/chat"
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"<context>\n{context}\n</context>\n\nВопрос: {query}"},
        ],
        "stream": False,
        "options": {"temperature": 0.1},
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        answer = data["message"]["content"]
        logger.info("generated_answer_ollama", model=settings.ollama_model, query=query[:80], answer_len=len(answer))
        return answer


async def _generate_gemini(query: str, context: str) -> str:
    """Generate answer using Gemini API with retry and model fallback."""
    client = genai.Client(api_key=settings.gemini_api_key)
    contents = f"<context>\n{context}\n</context>\n\nВопрос: {query}"

    for model_name in GEMINI_MODELS:
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config={"system_instruction": SYSTEM_PROMPT, "temperature": 0.1},
                )
                answer = response.text or "Не удалось сгенерировать ответ."
                logger.info("generated_answer_gemini", model=model_name, query=query[:80])
                return answer
            except genai_errors.ServerError as e:
                logger.warning("gemini_server_error", model=model_name, attempt=attempt + 1, error=str(e)[:80])
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
            except genai_errors.ClientError as e:
                logger.error("gemini_client_error", model=model_name, error=str(e)[:200])
                break

    return "Сервис генерации временно недоступен. Попробуйте позже."


async def generate_answer(query: str, chunks: list[dict]) -> str:
    """Generate answer using configured LLM backend."""
    context = format_chunks_for_prompt(chunks)

    if settings.llm_backend == "ollama":
        return await _generate_ollama(query, context)
    return await _generate_gemini(query, context)
