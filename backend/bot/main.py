"""
Telegram bot entry point.

Usage:
    cd backend
    uv run python bot/main.py
"""

import asyncio
import logging

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from bot.handlers import get_graph, router

logger = structlog.get_logger()


def _prewarm_models() -> None:
    """Load embedding model, reranker, and BM25 index at startup so first request is fast."""
    logger.info("prewarm_start", msg="Pre-warming models...")
    from app.core.embeddings import get_embedder
    from app.core.retrieval import get_retriever
    get_embedder()
    try:
        retriever = get_retriever()
        retriever.load_bm25_from_qdrant()
    except Exception as e:
        logger.warning("prewarm_bm25_skipped", msg=f"Qdrant unavailable, BM25 will load on first request: {e}")
    if settings.enable_reranking:
        from app.core.reranker import get_reranker
        get_reranker()
    get_graph()
    logger.info("prewarm_done", msg="Models ready. Bot is accepting requests.")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("bot_start", msg="Starting Telegram bot...")

    _prewarm_models()

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("bot_polling", msg="Bot is running. Press Ctrl+C to stop.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
