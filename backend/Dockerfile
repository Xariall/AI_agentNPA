FROM python:3.13-slim

WORKDIR /app

# System deps for opencv and docling
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Cache-bust: always rebuild model download and app layers
ARG REBUILD_MODELS=1
# Pre-download ML models so runtime has no download spikes (avoids OOM kills)
RUN /app/.venv/bin/python -c "\
from sentence_transformers import SentenceTransformer, CrossEncoder; \
print('Downloading intfloat/multilingual-e5-small...'); \
SentenceTransformer('intfloat/multilingual-e5-small'); \
print('Downloading BAAI/bge-reranker-v2-m3...'); \
CrossEncoder('BAAI/bge-reranker-v2-m3'); \
print('Models ready.')"

COPY app/ ./app/
COPY scripts/ ./scripts/

CMD ["sh", "-c", "/app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
