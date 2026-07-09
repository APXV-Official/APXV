"""Unicode normalization before PII detection — homoglyph and zero-width defense."""

from __future__ import annotations

import unicodedata
from typing import Any, Dict, Union

CONFUSABLES: Dict[str, str] = {
    "Ð°": "a",
    "Ð": "A",
    "Ð’": "B",
    "Ð¡": "C",
    "Ð•": "E",
    "Ð": "H",
    "Ð†": "I",
    "Ðˆ": "J",
    "Ðš": "K",
    "Ðœ": "M",
    "Ðž": "O",
    "Ð ": "P",
    "Ð…": "S",
    "Ð¢": "T",
    "Ð¥": "X",
    "Ò®": "Y",
    "Ðµ": "e",
    "Ð¾": "o",
    "Ñ€": "p",
    "Ñ": "c",
    "Ñƒ": "y",
    "Ñ…": "x",
    "Ñ•": "s",
    "Î‘": "A",
    "Î’": "B",
    "Î•": "E",
    "Î–": "Z",
    "Î—": "H",
    "Î™": "I",
    "Îš": "K",
    "Îœ": "M",
    "Î": "N",
    "ÎŸ": "O",
    "Î¡": "P",
    "Î¤": "T",
    "Î¥": "Y",
    "Î§": "X",
    "Î±": "a",
    "Î²": "b",
    "Î³": "y",
    "Îµ": "e",
    "Î¹": "i",
    "Îº": "k",
    "Î½": "n",
    "Î¿": "o",
    "Ï": "p",
    "Ï„": "t",
    "Ï…": "y",
    "Ï‡": "x",
    "ï¼¡": "A",
    "ï¼º": "Z",
    "ï½": "a",
    "ï½š": "z",
    "ï¼": "0",
    "ï¼™": "9",
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
    "â€": "-",
    "â€‘": "-",
    "â€’": "-",
    "–": "-",
    "—": "-",
    "â€•": "-",
    "â„": "/",
    "âˆ•": "/",
    "â€¤": ".",
    "â€¥": ".",
    "â€¦": ".",
    "ï´¾": "(",
    "ï´¿": ")",
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