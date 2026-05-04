import json
import re
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.graph.rag_graph import build_graph

router = Router()

_graph = None

EVAL_RESULTS_DIR = Path(__file__).resolve().parent.parent / "eval" / "results"

DIVIDER = "──────────────────────"


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def _main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Метрики", callback_data="show_metrics"),
            InlineKeyboardButton(text="🔄 Запустить eval", callback_data="eval_confirm"),
        ]
    ])


def _clean_answer(answer: str) -> str:
    """Strip the LLM-generated sources block — we render our own."""
    answer = re.sub(r"\n*Источники\s*:.*$", "", answer, flags=re.DOTALL | re.IGNORECASE)
    return answer.strip()


def _format_sources(sources: list[dict]) -> str:
    if not sources:
        return ""
    lines = [f"\n{DIVIDER}\n📄 <b>Источники:</b>\n"]
    seen = set()
    num = 1
    for s in sources:
        fname = s.get("doc_filename", "")
        article = s.get("article", "")
        if fname in seen:
            continue
        seen.add(fname)
        label = re.sub(r"\.docx$", "", fname, flags=re.IGNORECASE)
        label = re.sub(r"^\d+\.\s*", "", label)
        if article and article.lower() not in ("anchor", ""):
            lines.append(f"<b>{num}.</b> {label}\n    <i>└ {article}</i>")
        else:
            lines.append(f"<b>{num}.</b> {label}")
        num += 1
    return "\n".join(lines)


def _format_confidence(confidence: str) -> str:
    return {
        "high":   "🟢 <i>Высокая уверенность</i>",
        "medium": "🟡 <i>Средняя уверенность</i>",
        "low":    "🔴 <i>Низкая уверенность</i>",
    }.get(confidence, "")


def _build_answer_message(answer: str, sources: list[dict], confidence: str) -> str:
    clean = _clean_answer(answer)
    conf_line = _format_confidence(confidence)
    sources_block = _format_sources(sources)

    parts = [f"💬 <b>Ответ</b>\n\n{clean}"]
    if conf_line:
        parts.append(f"\n{conf_line}")
    if sources_block:
        parts.append(sources_block)
    return "".join(parts)


def _load_latest_metrics() -> dict | None:
    if not EVAL_RESULTS_DIR.exists():
        return None
    files = sorted(EVAL_RESULTS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return None
    with open(files[0], encoding="utf-8") as f:
        data = json.load(f)
    return {"metrics": data.get("metrics", {}), "filename": files[0].name}


def _format_metrics(metrics: dict, filename: str) -> str:
    r = metrics.get("retrieval", {})
    g = metrics.get("generation", {})
    p = metrics.get("performance", {})
    return (
        f"📊 <b>Последние метрики</b>\n"
        f"<i>{filename}</i>\n\n"
        f"{DIVIDER}\n"
        f"<b>🔍 Retrieval</b>\n"
        f"  Hit Rate@1:  <b>{r.get('hit_rate@1', 0):.1%}</b>\n"
        f"  Hit Rate@3:  {r.get('hit_rate@3', 0):.1%}\n"
        f"  Hit Rate@5:  {r.get('hit_rate@5', 0):.1%}\n"
        f"  MRR:         {r.get('mrr', 0):.3f}\n\n"
        f"<b>✍️ Generation</b>\n"
        f"  Keyword Coverage:          {g.get('keyword_coverage', 0):.1%}\n"
        f"  Refusal Correctness:       {g.get('refusal_correctness', 0):.1%}\n"
        f"  Verification Failure Rate: {g.get('verification_failure_rate', 0):.1%}\n\n"
        f"<b>⚡️ Performance</b>\n"
        f"  p50: {p.get('latency_p50', 0):.0f}ms\n"
        f"  p95: {p.get('latency_p95', 0):.0f}ms"
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        f"👋 <b>Здравствуйте!</b>\n\n"
        f"При запросе модель отвечает в среднем 1–3 минуты.\n\n"
        f"Кнопки:\n"
        f"— Метрики — показывает последнюю проверку модели\n"
        f"— Запустить eval — запускает проверку",
        reply_markup=_main_keyboard(),
    )


@router.message(Command("metrics_help"))
async def cmd_metrics_help(message: Message) -> None:
    await message.answer(
        "<b>Retrieval</b> — качество поиска релевантных документов:\n"
        "  <b>Hit Rate@1/3/5</b> — как часто нужный документ попадает в топ 1/3/5 результатов\n"
        "  <b>MRR</b> — насколько высоко в выдаче находится правильный ответ\n\n"
        "<b>Generation</b> — качество ответов модели:\n"
        "  <b>Keyword Coverage</b> — доля ключевых слов из эталона в ответе\n"
        "  <b>Refusal Correctness</b> — корректность отказов, когда модель не должна отвечать\n"
        "  <b>Verification Failure Rate</b> — доля ошибок при проверке фактов\n\n"
        "<b>Performance</b> — производительность:\n"
        "  <b>Latency p50</b> — медианное время ответа\n"
        "  <b>Latency p95</b> — время ответа в худших 5% случаев",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "show_metrics")
async def cb_show_metrics(callback: CallbackQuery) -> None:
    await callback.answer()
    result = _load_latest_metrics()
    if result is None:
        await callback.message.answer("⚠️ Результаты eval не найдены. Сначала запустите eval.")
        return
    await callback.message.answer(
        _format_metrics(result["metrics"], result["filename"]),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "eval_confirm")
async def cb_eval_confirm(callback: CallbackQuery) -> None:
    await callback.answer()
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, запустить", callback_data="eval_run"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="eval_cancel"),
        ]
    ])
    await callback.message.answer(
        f"⚠️ <b>Запуск eval</b>\n\n"
        f"Займёт примерно 30-40 минут и нагружает систему.\n\n"
        f"Запустить оценку?",
        reply_markup=confirm_kb,
    )


@router.callback_query(F.data == "eval_cancel")
async def cb_eval_cancel(callback: CallbackQuery) -> None:
    await callback.answer("Отменено")
    await callback.message.edit_text("❌ Запуск eval отменён.")


@router.callback_query(F.data == "eval_run")
async def cb_eval_run(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text("⏳ Запускаю eval, это займёт несколько минут...")

    try:
        from eval.runner import main as eval_main
        metrics = await eval_main("tg_run")
    except Exception as e:
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка при запуске eval:</b>\n<code>{e}</code>",
            parse_mode="HTML",
        )
        return

    r = metrics.get("retrieval", {})
    g = metrics.get("generation", {})
    text = (
        f"✅ <b>Eval завершён</b>\n\n"
        f"{DIVIDER}\n"
        f"Hit Rate@1:          <b>{r.get('hit_rate@1', 0):.1%}</b>\n"
        f"Hit Rate@5:          {r.get('hit_rate@5', 0):.1%}\n"
        f"MRR:                 {r.get('mrr', 0):.3f}\n"
        f"Keyword Coverage:    {g.get('keyword_coverage', 0):.1%}\n"
        f"Refusal Correctness: {g.get('refusal_correctness', 0):.1%}"
    )
    await callback.message.edit_text(text, parse_mode="HTML")


@router.message()
async def handle_question(message: Message) -> None:
    if not message.text:
        return

    thinking = await message.answer("⏳ <i>Обрабатываю запрос...</i>", parse_mode="HTML")

    try:
        state = await get_graph().ainvoke({"question": message.text})
    except Exception as e:
        await thinking.delete()
        await message.answer(f"⚠️ <b>Ошибка:</b> <code>{e}</code>", parse_mode="HTML")
        return

    await thinking.delete()

    if state.get("refused"):
        await message.answer(
            f"⛔️ <b>Вне компетенции</b>\n\n"
            f"Этот вопрос выходит за рамки базы знаний.\n"
            f"Я отвечаю только на вопросы по НПА в сфере медицинских изделий РК.",
            parse_mode="HTML",
        )
        return

    text = _build_answer_message(
        answer=state.get("answer", "Не удалось получить ответ."),
        sources=state.get("sources", []),
        confidence=state.get("confidence", ""),
    )
    await message.answer(text, parse_mode="HTML")
