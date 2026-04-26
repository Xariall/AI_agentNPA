import re
import uuid

import structlog

logger = structlog.get_logger()

# Patterns for structure detection in Kazakh/Russian legal documents
CHAPTER_RE = re.compile(r"^#{1,3}\s*(?:Глава|ГЛАВА|Раздел|РАЗДЕЛ)\s+(\S+)", re.MULTILINE)
ARTICLE_RE = re.compile(r"^#{0,3}\s*(?:Статья|СТАТЬЯ)\s+(\d+[\-\.]?\d*)", re.MULTILINE)
PARAGRAPH_RE = re.compile(r"^(\d+)\.\s", re.MULTILINE)
SUBPARAGRAPH_RE = re.compile(r"^(\d+)\)\s", re.MULTILINE)

MAX_CHUNK_TOKENS = 1500
APPROX_CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    return len(text) // APPROX_CHARS_PER_TOKEN


def _build_context_header(doc_meta: dict, chapter: str, article: str) -> str:
    """Build a contextual header like [Приказ №123 от 02.10.2020] Глава 3. Статья 15."""
    parts = []

    doc_type = doc_meta.get("doc_type", "")
    doc_number = doc_meta.get("doc_number", "")
    doc_date = doc_meta.get("doc_date", "")

    doc_label = doc_type.capitalize() if doc_type else "Документ"
    if doc_number:
        doc_label += f" №{doc_number}"
    if doc_date:
        doc_label += f" от {doc_date}"
    parts.append(f"[{doc_label}]")

    if chapter:
        parts.append(f"Глава {chapter}.")
    if article:
        parts.append(f"Статья {article}.")

    return " ".join(parts)


def _split_by_pattern(text: str, pattern: re.Pattern) -> list[tuple[str, str]]:
    """Split text by regex pattern, return list of (match_value, block_text)."""
    matches = list(pattern.finditer(text))
    if not matches:
        return [("", text)]

    blocks = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block_text = text[start:end].strip()
        blocks.append((match.group(1), block_text))

    # Text before first match
    preamble = text[: matches[0].start()].strip()
    if preamble:
        blocks.insert(0, ("0", preamble))

    return blocks


def _fallback_split(text: str, max_chars: int, overlap: int = 200) -> list[str]:
    """Simple character-based split with overlap as last resort."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        # Try to break at sentence boundary
        if end < len(text):
            last_period = text.rfind(".", start, end)
            last_newline = text.rfind("\n", start, end)
            break_at = max(last_period, last_newline)
            if break_at > start + max_chars // 2:
                end = break_at + 1
        chunks.append(text[start:end].strip())
        start = end - overlap if end < len(text) else end
    return [c for c in chunks if c]


def chunk_document(doc: dict) -> list[dict]:
    """
    Structure-aware chunking for legal documents.

    Algorithm:
    1. Split by articles (Статья N)
    2. If article > 1500 tokens, split by paragraphs (N.)
    3. If still too long, fallback to char-based split with overlap
    4. Add contextual header to each chunk
    """
    markdown = doc["markdown"]
    metadata = doc["metadata"]
    chunks = []

    max_chars = MAX_CHUNK_TOKENS * APPROX_CHARS_PER_TOKEN

    # First try to find chapters
    current_chapter = ""
    chapter_blocks = _split_by_pattern(markdown, CHAPTER_RE)

    for chapter_num, chapter_text in chapter_blocks:
        if chapter_num != "0":
            current_chapter = chapter_num

        # Within each chapter, split by articles
        article_blocks = _split_by_pattern(chapter_text, ARTICLE_RE)

        for article_num, article_text in article_blocks:
            current_article = article_num if article_num != "0" else ""

            if _estimate_tokens(article_text) <= MAX_CHUNK_TOKENS:
                # Article fits in one chunk
                header = _build_context_header(metadata, current_chapter, current_article)
                chunks.append(_make_chunk(
                    text=article_text,
                    header=header,
                    metadata=metadata,
                    chapter=current_chapter,
                    article=current_article,
                    paragraph="",
                ))
            else:
                # Article too long — split by paragraphs
                para_blocks = _split_by_pattern(article_text, PARAGRAPH_RE)

                for para_num, para_text in para_blocks:
                    if _estimate_tokens(para_text) <= MAX_CHUNK_TOKENS:
                        header = _build_context_header(metadata, current_chapter, current_article)
                        chunks.append(_make_chunk(
                            text=para_text,
                            header=header,
                            metadata=metadata,
                            chapter=current_chapter,
                            article=current_article,
                            paragraph=para_num if para_num != "0" else "",
                        ))
                    else:
                        # Paragraph still too long — fallback split
                        sub_chunks = _fallback_split(para_text, max_chars)
                        for i, sub_text in enumerate(sub_chunks):
                            header = _build_context_header(metadata, current_chapter, current_article)
                            chunks.append(_make_chunk(
                                text=sub_text,
                                header=header,
                                metadata=metadata,
                                chapter=current_chapter,
                                article=current_article,
                                paragraph=f"{para_num}.{i + 1}" if para_num != "0" else str(i + 1),
                            ))

    # If no structure was found at all, do basic splitting
    if not chunks:
        logger.warning("no_structure_found", file=metadata.get("doc_filename", ""))
        sub_chunks = _fallback_split(markdown, max_chars)
        for i, sub_text in enumerate(sub_chunks):
            header = _build_context_header(metadata, "", "")
            chunks.append(_make_chunk(
                text=sub_text,
                header=header,
                metadata=metadata,
                chapter="",
                article="",
                paragraph=str(i + 1),
            ))

    logger.info("chunked_document", file=metadata.get("doc_filename", ""), chunks=len(chunks))
    return chunks


def _make_chunk(
    text: str,
    header: str,
    metadata: dict,
    chapter: str,
    article: str,
    paragraph: str,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "text": f"{header}\n\n{text}",
        "metadata": {
            "doc_filename": metadata.get("doc_filename", ""),
            "doc_type": metadata.get("doc_type", ""),
            "doc_number": metadata.get("doc_number", ""),
            "doc_date": metadata.get("doc_date", ""),
            "domain": metadata.get("domain", "medical_device"),
            "chapter": chapter,
            "article": article,
            "paragraph": paragraph,
            "raw_text": text,
        },
    }
