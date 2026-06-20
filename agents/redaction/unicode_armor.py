"""Unicode normalization before PII detection — homoglyph and zero-width defense."""

from __future__ import annotations

import unicodedata
from typing import Any, Dict, Union

CONFUSABLES: Dict[str, str] = {
    "а": "a",
    "А": "A",
    "В": "B",
    "С": "C",
    "Е": "E",
    "Н": "H",
    "І": "I",
    "Ј": "J",
    "К": "K",
    "М": "M",
    "О": "O",
    "Р": "P",
    "Ѕ": "S",
    "Т": "T",
    "Х": "X",
    "Ү": "Y",
    "е": "e",
    "о": "o",
    "р": "p",
    "с": "c",
    "у": "y",
    "х": "x",
    "ѕ": "s",
    "Α": "A",
    "Β": "B",
    "Ε": "E",
    "Ζ": "Z",
    "Η": "H",
    "Ι": "I",
    "Κ": "K",
    "Μ": "M",
    "Ν": "N",
    "Ο": "O",
    "Ρ": "P",
    "Τ": "T",
    "Υ": "Y",
    "Χ": "X",
    "α": "a",
    "β": "b",
    "γ": "y",
    "ε": "e",
    "ι": "i",
    "κ": "k",
    "ν": "n",
    "ο": "o",
    "ρ": "p",
    "τ": "t",
    "υ": "y",
    "χ": "x",
    "Ａ": "A",
    "Ｚ": "Z",
    "ａ": "a",
    "ｚ": "z",
    "０": "0",
    "９": "9",
}

ZERO_WIDTH_CHARS = (
    "\u200b",
    "\u200c",
    "\u200d",
    "\u200e",
    "\u200f",
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",
    "\u2060",
    "\u2061",
    "\u2062",
    "\u2063",
    "\u2064",
    "\ufeff",
    "\u2066",
    "\u2067",
    "\u2068",
    "\u2069",
)

PUNCTUATION_CONFUSABLES: Dict[str, str] = {
    "‐": "-",
    "‑": "-",
    "‒": "-",
    "–": "-",
    "—": "-",
    "―": "-",
    "⁄": "/",
    "∕": "/",
    "․": ".",
    "‥": ".",
    "…": ".",
    "﴾": "(",
    "﴿": ")",
}


def unicode_armor(text: str) -> str:
    if not text:
        return text
    normalized = text
    for char in ZERO_WIDTH_CHARS:
        normalized = normalized.replace(char, "")
    normalized = unicodedata.normalize("NFKC", normalized)
    return "".join(
        CONFUSABLES.get(ch) or PUNCTUATION_CONFUSABLES.get(ch) or ch for ch in normalized
    )


def preprocess_for_pii_detection(value: Any) -> Any:
    if value is None:
        return value
    if isinstance(value, str):
        return unicode_armor(value)
    if isinstance(value, list):
        return [preprocess_for_pii_detection(item) for item in value]
    if isinstance(value, dict):
        return {unicode_armor(str(k)): preprocess_for_pii_detection(v) for k, v in value.items()}
    return value


def detect_unicode_spoofing(text: str) -> bool:
    if not text:
        return False
    for char in ZERO_WIDTH_CHARS:
        if char in text:
            return True
    for char in text:
        if char in CONFUSABLES:
            return True
    return text != unicodedata.normalize("NFKC", text)