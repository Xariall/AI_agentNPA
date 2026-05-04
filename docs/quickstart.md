# Быстрый старт

## Требования

- Python 3.12+, [uv](https://docs.astral.sh/uv/)
- Docker (для Qdrant)
- Ollama (для локального LLM)
- Telegram Bot Token (получить у [@BotFather](https://t.me/BotFather))

---

## 1. Установка

```bash
git clone <repo>
cd npa-assistant/backend

cp .env.example .env
# Отредактируй .env (см. ниже)

uv sync
```

### Минимальный `.env` для локальной разработки

```env
LLM_BACKEND=ollama
OLLAMA_MODEL=qwen2.5:7b
QDRANT_HOST=localhost
QDRANT_PORT=6333
TELEGRAM_BOT_TOKEN=your_token_here
```

---

## 2. Запуск Qdrant

```bash
docker run -p 6333:6333 qdrant/qdrant
```

---

## 3. Индексация документов

Один раз при первом запуске (или при изменении корпуса):

```bash
# Полная переиндексация
uv run python -m scripts.ingest

# Добавить anchor-чанки (summary по документу)
uv run python scripts/add_anchors.py

# Добавить один документ
uv run python -m scripts.add_doc --file ../data/doc.docx --name "Название" --type docx
```

---

## 4. Запуск API

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Проверка: `http://localhost:8000/api/health`

---

## 5. Запуск Telegram-бота

```bash
uv run python -m bot.main
```

Бот готов к работе. Команды:
- `/start` — приветствие
- `/help` — инструкция
- `/metrics_help` — объяснение метрик качества

---

## Полный стек через Docker Compose

```bash
# Из корня проекта
docker compose up

# Первичная индексация
docker compose --profile setup run --rm ingest
```
