# Архитектура

## RAG Pipeline

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
           rerank            (BGE cross-encoder, скоры 0–1)
               ↓
           check_confidence  (порог 0.05; отказ если ниже)
               ↓
           generate          (топ-5 чанков без дублей → Gemini/Ollama)
               ↓
           verify            (упомянутые номера статей/решений есть в источниках)
               ↓
         SSE: status → sources → token stream → done
```

---

## Ключевые файлы

| Файл | Назначение |
|------|-----------|
| `app/graph/rag_graph.py` | LangGraph StateGraph — весь RAG pipeline |
| `app/core/retrieval.py` | `HybridRetriever`: dense + BM25 (pymorphy3) + RRF; `multi_search()` |
| `app/core/reranker.py` | BGE cross-encoder singleton; скоры 0–1 (sigmoid) |
| `app/core/generation.py` | Gemini (3-model fallback) + Ollama; `generate_query_variants()`, HyDE |
| `app/core/embeddings.py` | E5Embedder; `passage:` prefix для документов, `query:` для запросов |
| `app/core/query_classifier.py` | Keyword classifier: `"medical_device"`, `"medicine"`, `None` |
| `app/core/verification.py` | Проверка галлюцинаций: номера статей из ответа должны быть в чанках |
| `app/core/chunking.py` | Structure-aware chunking: Docling DOCX→MD, затем split по Глава/Статья/Пункт |
| `app/prompts/system.py` | System prompt (RU); строгий запрет на выдуманные номера статей |
| `bot/handlers.py` | Telegram handlers: /start, /help, /metrics_help, query flow |

---

## Технические решения

| Компонент | Выбор | Почему не альтернатива |
|-----------|-------|------------------------|
| Embedder | `intfloat/multilingual-e5-large` | Лучше ada-002 на русском; работает локально на M1 |
| Reranker | `BAAI/bge-reranker-v2-m3` | Многоязычный; скоры 0–1, не логиты как у mmarco |
| Hybrid search | Dense + BM25 + RRF | BM25 ловит точные термины НПА, которые dense пропускает |
| Multi-query | 3 варианта + HyDE | Расширяет recall при неоднозначных формулировках |
| Vector DB | Qdrant | Hybrid search, фильтрация по метаданным; vs Chroma/Weaviate |
| LLM prod | Gemini 2.5 Flash | 1M контекст, дёшево, хорошо на русском/казахском |
| LLM dev | qwen2.5:7b via Ollama | Локально без затрат API при итерациях |
| Chunking | Structure-aware | НПА имеют чёткую иерархию; чанки по статьям = точные ссылки |
| Orchestration | LangGraph | Условные рёбра для отказов; граф версионируется |

---

## Критические ограничения

**Embedding-модель должна совпадать с коллекцией**  
Qdrant-коллекция собрана с конкретной моделью. Смена модели = пересборка коллекции.

**BGE reranker: скоры 0–1**  
Не логиты. Старый mmarco-reranker выдавал логиты (-∞ … +∞). Пороги несовместимы.

**E5 prefix обязателен**  
`embed_query()` → `"query: "` prefix, `embed_documents()` → `"passage: "` prefix.  
Без них качество retrieval заметно падает.

**BM25 грузится при старте**  
`load_bm25_from_qdrant()` забирает все 3600+ точек (~5с). Health endpoint доступен сразу.

**Multi-query и латентность**  
4 параллельных варианта × (retrieval + rerank) даёт ~71с p50 на Railway.  
Это trade-off: recall растёт, скорость падает.

---

## Что было непросто

**Qdrant API breaking change** — qdrant-client ≥1.17 убрал `search()`, заменил на `query_points()`.

**BGE vs mmarco** — mmarco выдавал логиты, BGE — sigmoid. Пороги несовместимы, пришлось перекалибровать по eval.

**Refusal на edge cases** — «Как зарегистрировать лекарство» получает высокий rerank-score, потому что в корпусе есть НПА о регистрации. Keyword classifier закрывает основные случаи.

**Structure-aware chunking** — DOCX → Docling → Markdown с заголовками `## Глава 1.`. Regex по паттернам Статья/Пункт даёт семантически цельные блоки вместо случайных 512-токенных кусков.
