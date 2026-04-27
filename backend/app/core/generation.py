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


_HYDE_PROMPT = """Ты — эксперт по нормативным правовым актам в сфере медицинских изделий Казахстана и ЕАЭС.

Напиши короткий фрагмент текста (2-4 предложения), который мог бы содержаться в официальном нормативном документе и отвечал бы на следующий вопрос. Пиши в стиле официального юридического документа на русском языке. Не упоминай вопрос — пиши только сам текст документа.

Вопрос: {query}"""


async def generate_hypothetical_doc(query: str) -> str:
    """Generate a hypothetical document passage (HyDE) for the query."""
    prompt = _HYDE_PROMPT.format(query=query)

    try:
        if settings.llm_backend == "ollama":
            url = f"{settings.ollama_base_url}/api/chat"
            payload = {
                "model": settings.ollama_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.2},
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                text = response.json()["message"]["content"].strip()
        else:
            client = genai.Client(api_key=settings.gemini_api_key)
            text = ""
            for model_name in GEMINI_MODELS:
                try:
                    resp = await client.aio.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config={"temperature": 0.2},
                    )
                    text = (resp.text or "").strip()
                    break
                except genai_errors.ServerError:
                    await asyncio.sleep(RETRY_DELAY)

        logger.info("hyde_generated", query=query[:60], passage_len=len(text))
        return text

    except Exception as e:
        logger.warning("hyde_failed", error=str(e)[:100])
        return ""


_MULTI_QUERY_PROMPT = """Ты помогаешь улучшить поиск по нормативным правовым актам Казахстана.

Задание: напиши 3 альтернативные формулировки вопроса на РУССКОМ ЯЗЫКЕ, используя разные юридические термины и синонимы. Все формулировки должны быть строго на русском языке.
Каждую формулировку напиши на отдельной строке. Не нумеруй строки. Не добавляй пояснений.

Вопрос: {query}"""


async def generate_query_variants(query: str) -> list[str]:
    """Generate alternative query formulations for multi-query retrieval."""
    prompt = _MULTI_QUERY_PROMPT.format(query=query)

    try:
        if settings.llm_backend == "ollama":
            url = f"{settings.ollama_base_url}/api/chat"
            payload = {
                "model": settings.ollama_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.3},
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                text = response.json()["message"]["content"]
        else:
            client = genai.Client(api_key=settings.gemini_api_key)
            text = ""
            for model_name in GEMINI_MODELS:
                try:
                    resp = await client.aio.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config={"temperature": 0.3},
                    )
                    text = resp.text or ""
                    break
                except genai_errors.ServerError:
                    await asyncio.sleep(RETRY_DELAY)

        import re as _re
        variants = [line.strip() for line in text.strip().splitlines() if line.strip()]
        # Keep only lines that are purely Russian (Cyrillic + common punctuation, no CJK/Arabic/etc.)
        variants = [
            v for v in variants
            if _re.search(r"[а-яА-ЯёЁ]", v)
            and not _re.search(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0600-\u06ff]", v)
            and v != query
        ][:3]
        logger.info("query_variants_generated", original=query[:60], count=len(variants))
        return variants

    except Exception as e:
        logger.warning("query_variants_failed", error=str(e)[:100])
        return []
