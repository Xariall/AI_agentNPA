import re
from pathlib import Path

import structlog
from docling.document_converter import DocumentConverter

logger = structlog.get_logger()


# Filenames that indicate a pure medicine/pharmaceutical document
_MEDICINE_FILENAME_SIGNALS = [
    "лекарственн",
    "фармацевт",
    "композитн",  # covers joint medicine+МИ orders
]


def _detect_domain(doc_type: str, filename: str) -> str:
    """
    Detect document domain from doc_type and filename only.

    Using full-text keywords was unreliable: almost every Приказ references
    the Кодекс in its preamble, causing 38% of medical-device documents to be
    mis-tagged as 'general'. We now rely on the structured doc_type field and
    filename signals instead.
    """
    if doc_type == "кодекс":
        return "general"

    fn_lower = filename.lower()
    for signal in _MEDICINE_FILENAME_SIGNALS:
        if signal in fn_lower:
            return "medicine"

    return "medical_device"


def extract_doc_metadata(text: str, filename: str) -> dict:
    """Extract document metadata from the first 2000 chars using regex."""
    header = text[:2000]
    metadata = {"doc_filename": filename, "doc_type": "", "doc_number": "", "doc_date": "", "domain": ""}

    # Detect document type
    lower = header.lower()
    if "приказ" in lower:
        metadata["doc_type"] = "приказ"
    elif "решение" in lower:
        metadata["doc_type"] = "решение"
    elif "кодекс" in lower:
        metadata["doc_type"] = "кодекс"
    elif "постановление" in lower:
        metadata["doc_type"] = "постановление"
    elif "закон" in lower:
        metadata["doc_type"] = "закон"
    elif "соглашение" in lower:
        metadata["doc_type"] = "соглашение"

    # Extract document number
    num_match = re.search(r"№\s*([\w\-/]+)", header)
    if num_match:
        metadata["doc_number"] = num_match.group(1).strip()

    # Extract date
    date_match = re.search(
        r"от\s+(\d{1,2})\s*[\.\s]?\s*(\w+)\s+(\d{4})\s*(?:года|г\.?)?",
        header,
    )
    if date_match:
        metadata["doc_date"] = f"{date_match.group(1)} {date_match.group(2)} {date_match.group(3)}"

    # Fallback: date from filename
    if not metadata["doc_date"]:
        date_fn = re.search(r"(\d{2}\.\d{2}\.\d{4})", filename)
        if date_fn:
            metadata["doc_date"] = date_fn.group(1)

    # Fallback: number from filename
    if not metadata["doc_number"]:
        num_fn = re.search(r"№\s*([\w\-/]+)", filename)
        if num_fn:
            metadata["doc_number"] = num_fn.group(1).strip()

    metadata["domain"] = _detect_domain(metadata["doc_type"], filename)

    return metadata


def parse_document(file_path: Path) -> dict:
    """Parse a single document using Docling, return markdown + metadata."""
    logger.info("parsing_document", file=file_path.name)

    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    markdown = result.document.export_to_markdown()

    metadata = extract_doc_metadata(markdown, file_path.name)
    logger.info(
        "parsed_document",
        file=file_path.name,
        doc_type=metadata["doc_type"],
        doc_number=metadata["doc_number"],
        chars=len(markdown),
    )

    return {
        "filename": file_path.name,
        "markdown": markdown,
        "metadata": metadata,
    }


def parse_all_documents(data_dir: Path) -> list[dict]:
    """Parse all DOCX/PDF files in the directory."""
    docs = []
    extensions = ("*.docx", "*.pdf", "*.doc")
    files = []
    for ext in extensions:
        files.extend(data_dir.glob(ext))

    files.sort(key=lambda f: f.name)
    logger.info("found_documents", count=len(files))

    for file_path in files:
        try:
            doc = parse_document(file_path)
            docs.append(doc)
        except Exception:
            logger.exception("parse_error", file=file_path.name)

    return docs
