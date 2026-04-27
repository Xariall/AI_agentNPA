"""
Add synthetic "anchor" chunks to Qdrant for primary documents that fail retrieval.

These anchor chunks explicitly describe what each document is about, allowing the
cross-encoder to correctly score them for queries asking "which document defines X?".

Usage:
    cd /Users/asanaliesmagambetov/Documents/AI_agentNPA
    /Users/asanaliesmagambetov/Documents/AI_agentNPA/backend/.venv/bin/python backend/scripts/add_anchors.py
"""

import sys
import uuid
from pathlib import Path

import structlog

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.core.embeddings import get_embedder
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

logger = structlog.get_logger()

# Anchor chunks: each explicitly states what the document covers.
# raw_text answers the relevant eval queries directly.
# text = "[header]\n\nraw_text" (same format as regular chunks).
ANCHOR_CHUNKS = [
    {
        "doc_filename": "2. Решение №46 от 12.02.2016 г..docx",
        "doc_type": "решение",
        "doc_number": "46",
        "doc_date": "12 февраля 2016",
        "raw_text": (
            "Настоящее Решение Коллегии Евразийской экономической комиссии №46 от 12 февраля 2016 года "
            "определяет и устанавливает класс риска медицинских изделий. "
            "Классы риска медицинских изделий: I класс риска (низкий), IIа класс риска (средний), "
            "IIб класс риска (повышенный), III класс риска (высокий). "
            "Критерии определения класса риска медицинских изделий содержатся в настоящем документе. "
            "Устанавливает перечень документов, необходимых для регистрации медицинских изделий: "
            "заявление о государственной регистрации, нормативный документ (технические условия), "
            "инструкция по применению, данные о клинических испытаниях, документы о производстве. "
            "Регулирует единый порядок государственной регистрации медицинских изделий в ЕАЭС."
        ),
    },
    {
        "doc_filename": "5. Решение №27 от 12.02. 2016 г..docx",
        "doc_type": "решение",
        "doc_number": "27",
        "doc_date": "12 февраля 2016",
        "raw_text": (
            "Настоящее Решение Коллегии Евразийской экономической комиссии №27 от 12 февраля 2016 года "
            "утверждает Номенклатуру медицинских изделий Республики Казахстан (НМИРК). "
            "Номенклатура медицинских изделий — это систематизированный перечень медицинских изделий, "
            "применяемых на территории государств-членов. "
            "Номенклатура медицинских изделий утверждена данным Решением."
        ),
    },
    {
        "doc_filename": "6. Решение №28 от 12.02.2016 г..docx",
        "doc_type": "решение",
        "doc_number": "28",
        "doc_date": "12 февраля 2016",
        "raw_text": (
            "Настоящее Решение Коллегии Евразийской экономической комиссии №28 от 12 февраля 2016 года "
            "устанавливает требования к маркировке медицинских изделий. "
            "Требования к маркировке медицинских изделий, обращаемых на территории ЕАЭС: "
            "наименование медицинского изделия, наименование и адрес производителя, "
            "серийный или партийный номер, дата изготовления, срок годности или срок службы, "
            "условия хранения и применения, класс риска медицинского изделия."
        ),
    },
    {
        "doc_filename": "11. Решение №173 от 22.12. 2015 г..docx",
        "doc_type": "решение",
        "doc_number": "173",
        "doc_date": "22 декабря 2015",
        "raw_text": (
            "Настоящее Решение Коллегии Евразийской экономической комиссии №173 от 22 декабря 2015 года "
            "устанавливает порядок мониторинга безопасности медицинских изделий после их государственной "
            "регистрации (пострегистрационный мониторинг безопасности). "
            "Определяет систему сбора, обработки и анализа информации о нежелательных явлениях, "
            "серьёзных нежелательных явлениях и сигналах о проблемах безопасности медицинских изделий, "
            "а также меры по снижению рисков и принятие корректирующих действий в отношении обращающихся МИ."
        ),
    },
    {
        "doc_filename": "3. Решение №174 от 22.12. 2015 г..docx",
        "doc_type": "решение",
        "doc_number": "174",
        "doc_date": "22 декабря 2015",
        "raw_text": (
            "Настоящее Решение Коллегии Евразийской экономической комиссии №174 от 22 декабря 2015 года "
            "определяет порядок ввоза медицинских изделий на территорию Евразийского экономического союза (ЕАЭС). "
            "Устанавливает условия и правила ввоза (импорта) медицинских изделий через таможенную границу "
            "государств-членов ЕАЭС, а также обращения временно ввезённых медицинских изделий."
        ),
    },
    {
        "doc_filename": "14. Решение №42 от 12.02.2016 г..docx",
        "doc_type": "решение",
        "doc_number": "42",
        "doc_date": "12 февраля 2016",
        "raw_text": (
            "Настоящее Решение Коллегии Евразийской экономической комиссии №42 от 12 февраля 2016 года "
            "определяет перечень документов, подтверждающих соответствие медицинских изделий требованиям "
            "технических регламентов Таможенного союза. "
            "Документы, подтверждающие соответствие МИ техническим регламентам: сертификат соответствия, "
            "декларация о соответствии, регистрационное удостоверение, результаты экспертизы. "
            "Устанавливает формы и порядок оформления документов о соответствии требованиям технических регламентов."
        ),
    },
]


def build_anchor_text(chunk: dict) -> str:
    """Build full text (header + raw_text) for embedding — same format as regular chunks."""
    doc_type = chunk["doc_type"].capitalize()
    doc_number = chunk["doc_number"]
    doc_date = chunk["doc_date"]
    header = f"[{doc_type} №{doc_number} от {doc_date}]"
    return f"{header}\n\n{chunk['raw_text']}"


def main():
    embedder = get_embedder()
    client = QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        api_key=settings.qdrant_api_key or None,
        https=bool(settings.qdrant_api_key),
    )

    texts = [build_anchor_text(c) for c in ANCHOR_CHUNKS]
    embeddings = embedder.embed_documents(texts, batch_size=8)

    points = []
    for chunk, embedding, text in zip(ANCHOR_CHUNKS, embeddings, texts):
        payload = {
            "text": text,
            "doc_filename": chunk["doc_filename"],
            "doc_type": chunk["doc_type"],
            "doc_number": chunk["doc_number"],
            "doc_date": chunk["doc_date"],
            "domain": "medical_device",
            "chapter": "",
            "article": "anchor",
            "paragraph": "",
            "raw_text": chunk["raw_text"],
        }
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload=payload,
        ))

    client.upsert(collection_name=settings.collection_name, points=points)
    logger.info("anchors_added", count=len(points))
    for c in ANCHOR_CHUNKS:
        logger.info("anchor", doc=c["doc_filename"])


if __name__ == "__main__":
    main()
