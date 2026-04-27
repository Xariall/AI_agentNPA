# Iteration Log

## v0 baseline (2026-04-25)
Model: qwen2.5:7b (local Ollama), rerank threshold: -2.0, top_k: 20

| Metric | Value |
|--------|-------|
| Hit Rate @ 1 | 27.3% |
| Hit Rate @ 5 | 45.5% |
| MRR | 0.341 |
| Keyword Coverage | 42.2% |
| Refusal Correctness | 85.7% |
| Verification Failure Rate | 34.6% |
| Latency p50 | 22s |
| Latency p95 | 38.5s |

**Провалы:**
- out_of_scope refusal: 33% (4/6 вопросов вне домена получили ответ)
- clinical_trials keyword_coverage: 0%
- import keyword_coverage: 0%
- verification_failure_rate слишком высокий (34.6%)

---

## v1 (2026-04-25) — fixes applied
Model: qwen2.5:7b (local Ollama), rerank threshold: 1.5, top_k: 30

Changes:
- rerank_score threshold: -2.0 → **1.5** (fix out-of-scope false answers)
- top_k dense search: 20 → **30** (fix clinical_trials/import misses)
- Prompts: explicit ban on inventing article numbers (fix verification failures)

| Metric | v0 | v1 | Delta |
|--------|----|----|-------|
| Hit Rate @ 1 | 27.3% | 27.3% | — |
| Hit Rate @ 5 | 45.5% | 45.5% | — |
| MRR | 0.341 | 0.341 | — |
| Keyword Coverage | 42.2% | **51.6%** | **+9.4pp** |
| Refusal Correctness | 85.7% | **92.9%** | **+7.2pp** |
| Verification Failure Rate | 34.6% | **8.3%** | **-26.3pp** |
| Latency p50 | 22s | 27s | +5s (model loading) |

**Wins:**
- Verification failure rate: 34.6% → 8.3% (prompt fix eliminated hallucinated citations)
- clinical_trials keyword_coverage: 0% → 66.7% (top_k=30 brings in relevant chunks)
- import keyword_coverage: 0% → 50.0%
- Refusal correctness improved: 85.7% → 92.9%

**Remaining failures:**
- q024 (drug registration): rerank_score=8.4 — retriever finds НПА docs with "регистрация",
  confused with МИ registration. Needs semantic domain filter or higher keyword specificity.
- q027 (traffic violations ПДД): rerank_score=1.59 — borderline above threshold (1.5),
  Кодекс chapter on sanctions matched. Raise threshold slightly or add domain keyword check.
- Hit Rate @5 unchanged: 45.5% — retrieval itself not improved, need BM25 hybrid or better chunking.

**Next iteration ideas:**
- Enable BM25 hybrid search (RRF) to improve Hit Rate
- Raise threshold to 2.0 and check refusal correctness
- Add domain keyword blocklist (ПДД, лекарство/препарат, зарплата)

Result file: `eval/results/v1_threshold_and_topk_20260425_221203.json`
