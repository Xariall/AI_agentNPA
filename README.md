# НПА Ассистент

RAG-ассистент по обращению медицинских изделий в Республике Казахстан.  
Отвечает строго на основе НПА, проверяет цитаты на галлюцинации, отказывается от вопросов вне домена.

**Интерфейс**: Telegram-бот (aiogram 3)  
**Деплой**: Railway + Qdrant Cloud  
**LLM**: Gemini 2.5 Flash (prod) / qwen2.5:7b via Ollama (local dev)

---

## Документация

| | |
|---|---|
| [Быстрый старт](docs/quickstart.md) | Локальный запуск: backend, бот, Qdrant |
| [Деплой на Railway](docs/deployment.md) | Production-деплой, переменные окружения |
| [Архитектура](docs/architecture.md) | RAG pipeline, технические решения, ограничения |
| [Eval & метрики](docs/eval.md) | Запуск оценки, метрики, история итераций |

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

---

## Структура проекта

```
npa-assistant/
├── backend/
│   ├── app/
│   │   ├── api/routes.py           # FastAPI endpoints + SSE streaming
│   │   ├── core/                   # retrieval, reranker, generation, embeddings...
│   │   ├── graph/rag_graph.py      # LangGraph StateGraph
│   │   └── prompts/system.py       # System prompt (RU)
│   ├── bot/
│   │   ├── main.py                 # aiogram 3 entry point
│   │   └── handlers.py             # /start, /help, /metrics_help, query flow
│   ├── scripts/
│   │   ├── ingest.py               # Парсинг DOCX → чанки → Qdrant
│   │   ├── add_anchors.py          # Синтетические summary-чанки
│   │   └── add_doc.py              # Добавить один документ в базу
│   ├── eval/
│   │   ├── dataset.yaml            # 28 вопросов с эталонными источниками
│   │   ├── runner.py               # Eval pipeline
│   │   ├── metrics.py              # Hit Rate, MRR и др.
│   │   └── results/                # JSON результатов каждого запуска
│   ├── ITERATIONS.md               # История итераций и метрики
│   └── Dockerfile
├── data/                           # Исходные DOCX с НПА
├── docs/                           # Документация
└── docker-compose.yml
```
