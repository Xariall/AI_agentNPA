import re

import structlog

logger = structlog.get_logger()

ARTICLE_MENTION_RE = re.compile(
    r"(?:статья|ст\.?)\s+(\d+[\-\.]?\d*)",
    re.IGNORECASE,
)
DOC_NUMBER_MENTION_RE = re.compile(r"№\s*([\d\-/]+)")


def verify_citations(answer: str, chunks: list[dict]) -> bool:
    """
    Return True if hallucinated citations detected.

    Checks that every article number and document number mentioned
    in the answer actually exists in the provided chunks.
    """
    mentioned_articles = set(ARTICLE_MENTION_RE.findall(answer.lower()))
    mentioned_doc_numbers = set(DOC_NUMBER_MENTION_RE.findall(answer))

    if not mentioned_articles and not mentioned_doc_numbers:
        return False

    available_articles: set[str] = set()
    available_doc_numbers: set[str] = set()
    for c in chunks:
        meta = c.get("metadata", {})
        if meta.get("article"):
            available_articles.add(str(meta["article"]).lower())
        if meta.get("doc_number"):
            available_doc_numbers.add(str(meta["doc_number"]))
        # Also extract articles from the raw text itself
        raw = meta.get("raw_text", c.get("text", ""))
        for match in ARTICLE_MENTION_RE.finditer(raw.lower()):
            available_articles.add(match.group(1))
        for match in DOC_NUMBER_MENTION_RE.finditer(raw):
            available_doc_numbers.add(match.group(1))

    hallucinated_articles = mentioned_articles - available_articles
    hallucinated_docs = mentioned_doc_numbers - available_doc_numbers

    if hallucinated_articles or hallucinated_docs:
        logger.warning(
            "hallucinated_citations",
            articles=list(hallucinated_articles),
            docs=list(hallucinated_docs),
        )
        return True

    return False
