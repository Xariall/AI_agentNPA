"""
Keyword-based query domain classifier.

Identifies whether a user query is about medical devices (МИ),
medicines (лекарства), or indeterminate.
"""

import re

# Strong signal keywords for each domain
_MEDICAL_DEVICE_SIGNALS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"медицинск\w*\s+издели\w*",
        r"медизделий?\b",
        r"медтехник\w*",
        r"\bМИ\b",
        r"класс[аеуы]?\s+риск\w*",
        r"регистрационн\w+\s+удостоверени\w+",
        r"обращени\w+\s+медицинск\w+\s+издели\w*",
        r"безопасност\w*\s+издели\w*",
        r"номенклатур\w+\s+медицинск\w*",
        r"технически\w+\s+документаци\w+",
    ]
]

_MEDICINE_SIGNALS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"лекарственн\w+\s+(?:средств\w*|препарат\w*)",
        r"лекарств\b",
        r"фармацевтическ\w+",
        r"аптек\w*",
        r"таблетк\w*",
        r"фармакологическ\w*",
        r"биологически\s+активн\w+\s+добавк\w*",
        r"субстанци\w+\s+лекарственн\w*",
    ]
]


def classify_query_domain(query: str) -> str | None:
    """
    Classify query domain.

    Returns:
        "medical_device" — query is about medical devices
        "medicine" — query is about medicines/pharmaceuticals
        None — ambiguous or unrelated
    """
    device_score = sum(1 for p in _MEDICAL_DEVICE_SIGNALS if p.search(query))
    medicine_score = sum(1 for p in _MEDICINE_SIGNALS if p.search(query))

    if device_score > 0 and medicine_score == 0:
        return "medical_device"
    if medicine_score > 0 and device_score == 0:
        return "medicine"
    # Both or neither — no filter
    return None
