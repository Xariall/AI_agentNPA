# Eval & Метрики

## Запуск оценки

```bash
cd backend
uv run python -m eval.runner <tag>

# Пример
uv run python -m eval.runner bge_reranker_v2

# Результат: eval/results/bge_reranker_v2_YYYYMMDD_HHMMSS.json
```

Eval запускается против живого графа с текущим `.env` — убедись, что Qdrant и LLM доступны.

---

## Метрики

### Retrieval

| Метрика | Описание |
|---------|----------|
| `hit_rate@1` | Нужный документ на 1-м месте |
| `hit_rate@3` | Нужный документ в топ-3 |
| `hit_rate@5` | Нужный документ в топ-5 |
| `mrr` | Mean Reciprocal Rank — учитывает позицию |

### Generation

| Метрика | Описание |
|---------|----------|
| `keyword_coverage` | Покрытие ключевых слов из эталонного ответа |
| `refusal_correctness` | Точность отказов на вопросы вне домена |
| `verification_failure_rate` | Доля ответов с галлюцинированными ссылками |

### Performance

| Метрика | Описание |
|---------|----------|
| `latency_p50` | Медианное время ответа (мс) |
| `latency_p95` | 95-й перцентиль |

---

## Целевые значения

| Метрика | Цель |
|---------|------|
| Hit Rate @ 1 | ≥ 80% |
| Hit Rate @ 5 | ≥ 90% |
| Refusal Correctness | ≥ 95% |

---

## Набор вопросов

28 вопросов в `eval/dataset.yaml`. Каждый вопрос содержит:

```yaml
- question: "..."
  expected_sources: ["doc_filename.docx"]
  keywords: ["ключевое", "слово"]
  should_refuse: false
  category: registration
  difficulty: medium
```

Категории: `classification`, `registration`, `nomenclature`, `labeling`, `expertise`, `out_of_scope` и др.

---

## Рабочий процесс при итерации

1. Внести изменения в код
2. Если изменился chunking или embeddings — переиндексировать: `uv run python -m scripts.ingest`
3. Если только добавляются anchor-чанки — `uv run python scripts/add_anchors.py`
4. Запустить eval: `uv run python -m eval.runner <описательный_тег>`
5. Сравнить метрики с предыдущим запуском
6. Зафиксировать в `backend/ITERATIONS.md`

---

## Команда в боте

`/metrics_help` — выводит объяснение каждой метрики прямо в Telegram.
