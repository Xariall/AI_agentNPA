# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG-based AI assistant for Kazakhstan medical device regulations (НПА — нормативные правовые акты). Answers questions strictly grounded in 27 regulatory documents (DOCX files), with citation verification, domain refusal, and eval-driven iteration.

**Production stack**: Railway (backend) + Vercel (frontend) + Qdrant Cloud (vector DB)  
**LLM**: Gemini 2.5 Flash (prod) / qwen2.5:7b via Ollama (local dev)  
**Embedding model**: `intfloat/multilingual-e5-large` (1024 dims, used for ingestion AND local inference)  
**Reranker**: `BAAI/bge-reranker-v2-m3` (BGE outputs 0–1 sigmoid scores, NOT logits)

---

## Commands

### Backend (Python, uv)

```bash
cd backend

# Install deps (uses uv.lock, CPU-only PyTorch)
uv sync

# Run dev server
uv run uvicorn app.main:app --reload --port 8000

# Run eval suite (from repo root)
cd ..
uv run python eval/runner.py <tag_name>
# Results → eval/results/<tag>_YYYYMMDD_HHMMSS.json

# Re-ingest documents (requires Qdrant running)
cd backend
uv run python -m scripts.ingest

# Add/refresh anchor chunks to existing Qdrant collection
uv run python scripts/add_anchors.py

# Lint
uv run ruff check app/
```

### Frontend (Next.js 16, React 19)

```bash
cd frontend
npm install
npm run dev     # http://localhost:3000
npm run build
```

### Full stack with Docker

```bash
# Start Qdrant + backend + frontend
docker compose up

# First-time ingestion (recreates the 'npa' collection)
docker compose --profile setup run --rm ingest
```

### Railway deployment

```bash
cd backend
railway up --detach

# Set env vars
railway variables --set "KEY=value"
railway variables   # view current
```

---

## Architecture

### Request flow

```
User query
  → Next.js (SSE stream via /api/query/stream rewrite)
    → FastAPI /api/query/stream
      → LangGraph StateGraph:
          rewrite           (abbreviation expansion: МИ→медицинские изделия, etc.)
          ↓
          classify_domain   (keyword classifier; refuses "medicine" queries)
          ↓
          multi_query       (parallel: 3 LLM-generated query variants + HyDE passage)
          ↓
          retrieve          (multi_search: each variant → dense+BM25+RRF, then cross-variant RRF)
          ↓
          rerank            (BGE cross-encoder; skipped if ENABLE_RERANKING=false)
          ↓
          check_confidence  (threshold: 0.05 for BGE 0-1 scores)
          ↓ (refused if low)
          generate          (top-5 deduplicated-by-doc chunks → Gemini/Ollama)
          ↓
          verify            (regex citation check: article numbers, doc numbers)
          ↓
        SSE: status → sources → token stream → done
```

### Key files

| File | Purpose |
|------|---------|
| `backend/app/graph/rag_graph.py` | LangGraph StateGraph — entire RAG pipeline logic |
| `backend/app/core/retrieval.py` | `HybridRetriever`: Qdrant dense + BM25 (pymorphy3 lemmatized) + RRF fusion; `multi_search()` runs per-query then cross-query RRF |
| `backend/app/core/reranker.py` | BGE cross-encoder singleton; scores are 0–1 (sigmoid) |
| `backend/app/core/generation.py` | Gemini (with 3-model fallback) + Ollama backends; `generate_query_variants()` and `generate_hypothetical_doc()` (HyDE) |
| `backend/app/core/embeddings.py` | E5Embedder singleton; uses `passage:` prefix for docs, `query:` prefix for queries (E5 requirement) |
| `backend/app/core/query_classifier.py` | Regex keyword classifier; returns `"medical_device"`, `"medicine"`, or `None` |
| `backend/app/core/verification.py` | Post-generation hallucination check: article numbers and doc numbers mentioned in answer must exist in retrieved chunks |
| `backend/app/core/chunking.py` | Structure-aware chunking: Docling DOCX→Markdown, then split by Глава/Статья/Пункт regex; adds contextual header `[Решение №46] Статья 5` to each chunk's text |
| `backend/app/prompts/system.py` | System prompt (Russian); STRICT rules against inventing article numbers |
| `backend/app/api/routes.py` | `/api/query` (sync JSON), `/api/query/stream` (SSE), `/api/health`, `/api/eval/latest`, `/api/eval/history` |
| `backend/scripts/ingest.py` | One-time: parse DOCX → chunk → embed → upload to Qdrant (recreates collection) |
| `backend/scripts/add_anchors.py` | Adds synthetic per-document summary chunks to improve retrieval for "which document defines X?" queries |
| `eval/runner.py` | Runs all 28 eval questions through the live graph, saves JSON results |
| `eval/dataset.yaml` | 28 questions with `expected_sources` (doc_filename), keywords, `should_refuse` flag |
| `eval/metrics.py` | `hit_rate@k`, `mrr`, `keyword_coverage`, `refusal_correctness`, `verification_failure_rate` |
| `eval/ITERATIONS.md` | Manual log of every eval run with metrics and diagnosis |
| `frontend/app/page.tsx` | Chat UI — SSE streaming, message list, source cards |
| `frontend/app/dashboard/page.tsx` | Metrics dashboard — reads `/api/eval/history` |

---

## Configuration (`backend/app/config.py`)

All settings read from environment / `.env`:

| Variable | Default | Notes |
|----------|---------|-------|
| `GEMINI_API_KEY` | `""` | Required for prod |
| `LLM_BACKEND` | `"ollama"` | `"ollama"` or `"gemini"` |
| `QDRANT_HOST` / `QDRANT_PORT` | `localhost:6333` | |
| `QDRANT_API_KEY` | `""` | Set for cloud Qdrant (enables HTTPS) |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-large` | Must match the model used for ingestion |
| `COLLECTION_NAME` | `"npa"` | Qdrant collection name |
| `RETRIEVAL_TOP_K` | `50` | Candidates before reranking |
| `RERANK_TOP_N` | `20` | Chunks passed to reranker |
| `RERANK_SCORE_THRESHOLD` | `0.05` | BGE 0–1 scale; low = reject |
| `ENABLE_RERANKING` | `true` | Set `false` on Railway to save ~570MB RAM |

---

## Critical Constraints

**Embedding dimension must match**: The Qdrant collection was built with `e5-large` (1024 dims). On Railway, `EMBEDDING_MODEL=intfloat/multilingual-e5-small` (384 dims) is set to save RAM — this means the Railway deployment CANNOT use the same Qdrant collection used locally. Separate collections are needed for each model.

**Reranker score scale**: BGE reranker outputs 0–1 (sigmoid). The old mmarco reranker used raw logits (-∞ to +∞). Thresholds and confidence levels are calibrated for BGE range. Do not mix these.

**E5 prefix requirement**: `embed_query()` uses `"query: "` prefix; `embed_documents()` uses `"passage: "` prefix. Omitting these degrades retrieval significantly.

**BM25 loads at startup**: `retriever.load_bm25_from_qdrant()` fetches all 3600+ points on startup (~5s). The health endpoint is available immediately; BM25 completes in background (5s sleep + load).

**Evaluation runs against the local graph**: `eval/runner.py` imports and runs `build_graph()` directly — it must be run with the same `.env` configuration (Qdrant URL, LLM backend) that you want to test.

---

## Eval Workflow

When improving retrieval/generation quality:

1. Make code changes
2. If chunking or embeddings changed: re-run `scripts/ingest.py` to rebuild the collection
3. If only adding anchor chunks: run `scripts/add_anchors.py`
4. Run: `uv run python eval/runner.py <descriptive_tag>`
5. Compare metrics to previous run
6. Update `eval/ITERATIONS.md` with changes, metrics, wins/failures

**Target metrics**: Hit Rate@1 ≥ 80%, Hit Rate@5 ≥ 90%, Refusal Correctness ≥ 95%

---

## Railway Production Notes

- Backend is deployed from `backend/` directory via `railway up`
- `ENABLE_RERANKING=false` is set on Railway (memory constraint ~512MB)
- `EMBEDDING_MODEL=intfloat/multilingual-e5-small` is set on Railway (smaller model)
- The Dockerfile pre-downloads models at build time to avoid OOM spikes at runtime
- `railway.toml` sets healthcheck path to `/api/health` with 120s timeout
