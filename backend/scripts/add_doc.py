"""
Add a single document (DOCX or TXT) to the existing Qdrant collection without full re-ingest.

Usage:
    cd backend
    uv run python -m scripts.add_doc --file ../НПА/raw/ndda_nmiрk.txt --name "ndda.kz — НМИРК" --type web
    uv run python -m scripts.add_doc --file ../НПА/raw/prikaz_127_2020.docx --name "Приказ ҚР ДСМ-127/2020" --type order

Supported formats: .txt, .md, .docx
"""

import argparse
import hashlib
import sys
from pathlib import Path

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.core.embeddings import get_embedder

logger = structlog.get_logger()


def _chunk_text(text: str, doc_name: str, doc_type: str, chunk_size: int = 800, overlap: int = 100) -> list[dict]:
    """Split plain text into overlapping chunks."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) > chunk_size and current:
            chunks.append(current.strip())
            # Keep overlap
            words = current.split()
            current = " ".join(words[-overlap // 6:]) + "\n\n" + para
        else:
            current = (current + "\n\n" + para).strip() if current else para

    if current.strip():
        chunks.append(current.strip())

    result = []
    for i, chunk_text in enumerate(chunks):
        chunk_id = int(hashlib.md5(f"{doc_name}:{i}".encode()).hexdigest(), 16) % (10 ** 15)
        # Prefix required by E5 model
        prefixed = f"passage: {chunk_text}"
        result.append({
            "id": chunk_id,
            "text": prefixed,
            "metadata": {
                "raw_text": chunk_text,
                "doc_filename": doc_name,
                "doc_type": doc_type,
                "doc_number": "",
                "article": f"chunk_{i + 1}",
                "paragraph": "",
                "chunk_index": i,
            },
        })
    return result


def _load_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8")
    elif suffix == ".docx":
        from docling.document_converter import DocumentConverter
        converter = DocumentConverter()
        result = converter.convert(str(path))
        return result.document.export_to_markdown()
    else:
        raise ValueError(f"Unsupported format: {suffix}. Use .txt, .md, or .docx")


def main():
    parser = argparse.ArgumentParser(description="Add a document to the RAG corpus")
    parser.add_argument("--file", required=True, help="Path to document (.txt, .md, .docx)")
    parser.add_argument("--name", required=True, help="Display name for this document")
    parser.add_argument("--type", default="supplementary", help="Document type (web, order, instruction, etc.)")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        logger.error("file_not_found", path=str(file_path))
        sys.exit(1)

    logger.info("loading_document", path=str(file_path))
    text = _load_text(file_path)
    logger.info("document_loaded", chars=len(text))

    chunks = _chunk_text(text, doc_name=args.name, doc_type=args.type)
    logger.info("chunked", count=len(chunks))

    logger.info("embedding")
    embedder = get_embedder()
    texts = [c["text"] for c in chunks]
    embeddings = embedder.embed_documents(texts, batch_size=32)

    qdrant = QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        api_key=settings.qdrant_api_key or None,
        https=bool(settings.qdrant_api_key),
    )

    points = []
    for chunk, embedding in zip(chunks, embeddings):
        payload = {"text": chunk["text"], **chunk["metadata"]}
        points.append(PointStruct(id=chunk["id"], vector=embedding, payload=payload))

    qdrant.upsert(collection_name=settings.collection_name, points=points)
    logger.info("uploaded", collection=settings.collection_name, chunks=len(points))
    print(f"\nДобавлено {len(points)} чанков из «{args.name}» в коллекцию '{settings.collection_name}'")


if __name__ == "__main__":
    main()
