# НПА Ассистент — RAG-система для нормативных правовых актов РК

AI-ассистент по обращению медицинских изделий в Республике Казахстан.  
Отвечает строго на основе НПА, проверяет цитаты против галлюцинаций, отказывается от вопросов вне домена.

**Интерфейс**: Telegram-бот (aiogram 3)  
**Деплой**: Railway (backend + bot) + Qdrant Cloud  
**LLM**: Gemini 2.5 Flash (prod) / qwen2.5:7b via Ollama (local dev)

---

## Метрики качества (eval-набор: 28 вопросов, запуск tg_run_20260427)

| Метрика | Значение |
|---------|----------|
| Hit Rate @ 1 | 63.6% |
| Hit Rate @ 3 | 86.4% |
| Hit Rate @ 5 | **95.5%** |
| MRR | 0.763 |
| Keyword Coverage | 56.5% |
| Refusal Correctness | 85.7% |
| Verification Failure Rate | 7.7% |
| Latency p50 | ~71s |

Полная история → [`backend/ITERATIONS.md`](backend/ITERATIONS.md)

---

## Архитектура

```
Telegram → aiogram bot
               ↓
         FastAPI /api/query/stream (SSE)
               ↓
         LangGraph StateGraph:
           rewrite           (расширение аббревиатур: МИ → медицинские изделия)
               ↓
           classify_domain   (keyword classifier; отказ на «лекарственные препараты»)
               ↓
           multi_query       (параллельно: 3 LLM-варианта запроса + HyDE-пассаж)
               ↓
           retrieve          (на каждый вариант: dense+BM25+RRF → cross-variant RRF)
               ↓
           rerank            (BGE cross-encoder BAAI/bge-reranker-v2-m3, скоры 0–1)
               ↓
           check_confidence  (порог 0.05; отказ если ниже)
               ↓
           generate          (топ-5 чанков без дублей → Gemini/Ollama)
               ↓
           verify            (regex: упомянутые номера статей/решений есть в источниках)
               ↓
         SSE: status → sources → token stream → done
```

---

## Технические решения

| Компонент | Выбор | Почему |
|-----------|-------|--------|
| Embedder | `intfloat/multilingual-e5-large` (1024d) | Лучше ada-002 на русском; работает локально |
| Reranker | `BAAI/bge-reranker-v2-m3` | Многоязычный cross-encoder; скоры 0–1 (sigmoid), не логиты |
| Hybrid search | Dense + BM25 (pymorphy3) + RRF | BM25 ловит точные термины из НПА, которые dense пропускает |
| Multi-query | 3 LLM-варианта + HyDE | Расширяет recall для неоднозначных формулировок |
| Vector DB | Qdrant Cloud | Hybrid search, фильтрация по метаданным |
| LLM (prod) | Gemini 2.5 Flash | 1M контекст, дёшево, хорошо на русском/казахском |
| LLM (dev) | qwen2.5:7b via Ollama | Локально, без затрат API при итерациях |
| Chunking | Structure-aware (Глава → Статья → Пункт) | НПА имеют чёткую иерархию; чанки по статьям = точные ссылки |
| Orchestration | LangGraph | Условные рёбра для отказов и повторов; граф версионируется |
| Bot | aiogram 3 (Telegram) | Markdown-форматирование, inline-кнопки, команды |

---

## Быстрый старт

### Требования

- Python 3.12+, [uv](https://docs.astral.sh/uv/)
- Docker + Docker Compose (для Qdrant локально)
- Ollama (для локального LLM)

### Локальная разработка

```bash
git clone <repo>
cd npa-assistant/backend

cp .env.example .env
# Заполни: QDRANT_HOST, GEMINI_API_KEY (или оставь LLM_BACKEND=ollama)
# Для бота: TELEGRAM_BOT_TOKEN

uv sync

# Запусти Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Первичная индексация документов
uv run python -m scripts.ingest

# Запуск API
uv run uvicorn app.main:app --reload --port 8000

# Запуск Telegram-бота (в отдельном терминале)
uv run python -m bot.main
```

### Railway (production)

```bash
cd backend
railway up --detach

# Переменные окружения
railway variables --set "GEMINI_API_KEY=..."
railway variables --set "TELEGRAM_BOT_TOKEN=..."
railway variables --set "QDRANT_URL=..."
railway variables --set "QDRANT_API_KEY=..."
railway variables --set "ENABLE_RERANKING=false"   # экономия RAM
railway variables --set "EMBEDDING_MODEL=intfloat/multilingual-e5-small"
```

---

## Eval: измерение качества

```bash
cd backend
uv run python -m eval.runner <tag>
# Результаты: eval/results/<tag>_YYYYMMDD_HHMMSS.json
```

**Метрики:**
- `hit_rate@1/3/5` — доля вопросов с нужным документом в топ-k
- `mrr` — Mean Reciprocal Rank
- `keyword_coverage` — покрытие ключевых слов эталонного ответа
- `refusal_correctness` — точность отказов на вопросы вне домена
- `verification_failure_rate` — доля ответов с галлюцинированными ссылками
- `latency_p50/p95` — перцентили времени ответа

Команда в боте: `/metrics_help` — объяснение каждой метрики.

---

## Структура проекта

```
npa-assistant/
├── backend/
│   ├── app/
│   │   ├── api/routes.py           # FastAPI endpoints + SSE streaming
│   │   ├── core/
│   │   │   ├── retrieval.py        # HybridRetriever: dense + BM25 + RRF
│   │   │   ├── reranker.py         # BGE cross-encoder (скоры 0–1)
│   │   │   ├── generation.py       # Gemini + Ollama; multi-query + HyDE
│   │   │   ├── embeddings.py       # E5Embedder (query:/passage: prefix)
│   │   │   ├── query_classifier.py # Keyword classifier: domain / refuse
│   │   │   └── verification.py     # Проверка галлюцинированных ссылок
│   │   ├── graph/rag_graph.py      # LangGraph StateGraph
│   │   └── prompts/system.py       # System prompt (RU)
│   ├── bot/
│   │   ├── main.py                 # aiogram 3 bot entry point
│   │   └── handlers.py             # /start, /help, /metrics_help, query flow
│   ├── scripts/
│   │   ├── ingest.py               # Парсинг DOCX → чанки → Qdrant
│   │   ├── add_anchors.py          # Синтетические summary-чанки по документу
│   │   └── add_doc.py              # Добавить один документ в базу
│   ├── eval/
│   │   ├── dataset.yaml            # 28 вопросов с эталонными источниками
│   │   ├── runner.py               # Eval pipeline
│   │   ├── metrics.py              # Hit Rate, MRR, и др.
│   │   └── results/                # JSON с результатами каждого запуска
│   ├── ITERATIONS.md               # История итераций и метрики
│   └── Dockerfile
├── data/                           # Исходные DOCX с НПА
├── docker-compose.yml
└── RAG_DEVELOPMENT.md              # Документация по обучению/настройке RAG
```

---

## Важные ограничения

**Embedding-модель должна совпадать** — Qdrant-коллекция собрана с `e5-large` (1024d). На Railway используется `e5-small` (384d) для экономии RAM — это отдельная коллекция.

**BGE reranker: скоры 0–1** — не логиты. Порог `RERANK_SCORE_THRESHOLD=0.05`. На Railway reranking отключён (`ENABLE_RERANKING=false`) из-за ограничений памяти (~512MB).

**E5 prefix** — `embed_query()` использует `"query: "`, `embed_documents()` использует `"passage: "`. Без префиксов качество заметно хуже.

**BM25 грузится при старте** — `load_bm25_from_qdrant()` забирает все 3600+ точек (~5с). Health endpoint доступен сразу; BM25 готов через ~5с.

---

## Что было непросто

**Qdrant API breaking change** — qdrant-client ≥1.17 убрал `search()`, заменил на `query_points()`. Правка в одном файле.

**BGE vs mmarco** — mmarco выдавал логиты (-5 … +12), BGE — sigmoid (0–1). Пороги несовместимы, пришлось перекалибровать.

**Multi-query латентность** — 4 параллельных варианта × (retrieval + rerank) даёт ~70с p50 на Railway. Trade-off между recall и скоростью.

**Refusal на out-of-scope** — «Как зарегистрировать лекарство» получает высокий rerank-score, потому что в корпусе есть НПА о регистрации. Keyword classifier закрывает основные случаи, edge cases остаются.

---

## Roadmap

- [ ] Снизить латентность: кэш эмбеддингов, async reranker
- [ ] Улучшить refusal: LLM-based domain classifier вместо keyword
- [ ] Fine-tuning embedder на парах (вопрос, эталонный чанк)
- [ ] LLM-as-a-judge для расширения eval-набора
- [ ] Казахскоязычный интерфейс бота

---

*Сделано на Python + LangGraph + Qdrant + aiogram. Данные — публичные НПА РК и ЕАЭС.*
