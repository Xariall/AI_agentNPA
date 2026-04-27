"""
Ingest script: parse documents, chunk, embed, and upload to Qdrant.

Usage:
    cd backend
    uv run python -m scripts.ingest
"""

import json
import sys
from pathlib import Path

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

# Add backend to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.core.chunking import chunk_document
from app.core.embeddings import get_embedder
from app.core.parsing import parse_all_documents

logger = structlog.get_logger()


def main():
    data_dir = Path(settings.data_dir)
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    if not raw_dir.exists():
        logger.error("raw_dir_missing", path=str(raw_dir))
        sys.exit(1)

    # Step 1: Parse documents
    logger.info("step_1", msg="Parsing documents...")
    docs = parse_all_documents(raw_dir)
    logger.info("parsed", count=len(docs))

    # Step 2: Chunk documents
    logger.info("step_2", msg="Chunking documents...")
    all_chunks = []
    for doc in docs:
        chunks = chunk_document(doc)
        all_chunks.extend(chunks)
    logger.info("chunked", total_chunks=len(all_chunks))

    # Save chunks for debugging
    chunks_path = processed_dir / "chunks.json"
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    logger.info("saved_chunks", path=str(chunks_path))

    # Step 3: Compute embeddings
    logger.info("step_3", msg="Computing embeddings...")
    embedder = get_embedder()
    texts = [c["text"] for c in all_chunks]
    embeddings = embedder.embed_documents(texts, batch_size=32)
    logger.info("embedded", count=len(embeddings))

    # Step 4: Upload to Qdrant
    logger.info("step_4", msg="Uploading to Qdrant...")
    qdrant = QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        api_key=settings.qdrant_api_key or None,
        https=bool(settings.qdrant_api_key),
    )

    # Recreate collection
    collections = [c.name for c in qdrant.get_collections().collections]
    if settings.collection_name in collections:
        qdrant.delete_collection(settings.collection_name)
        logger.info("deleted_collection", name=settings.collection_name)

    qdrant.create_collection(
        collection_name=settings.collection_name,
        vectors_config=VectorParams(
            size=embedder.dimension,
            distance=Distance.COSINE,
        ),
    )
    logger.info("created_collection", name=settings.collection_name, dim=embedder.dimension)

    # Upload in batches
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch_chunks = all_chunks[i : i + batch_size]
        batch_embeddings = embeddings[i : i + batch_size]

        points = []
        for chunk, embedding in zip(batch_chunks, batch_embeddings):
            payload = {
                "text": chunk["text"],
                **chunk["metadata"],
            }
            points.append(PointStruct(
                id=chunk["id"],
                vector=embedding,
                payload=payload,
            ))

        qdrant.upsert(collection_name=settings.collection_name, points=points)
        logger.info("uploaded_batch", start=i, end=i + len(batch_chunks))

    logger.info("ingest_complete", total_chunks=len(all_chunks))
    print(f"\nDone! {len(all_chunks)} chunks indexed in collection '{settings.collection_name}'")


if __name__ == "__main__":
    main()
