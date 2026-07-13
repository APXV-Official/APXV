"""APX redaction package — format parsing, unicode armor, and entity-aware engine."""

from .backends import RedactionBackendRegistry
from .engine import (
    APXVRedactionEngine,
    APXRedactionEngine,
    REDACTION_ENGINE_VERSION,
    deep_redact_with_count,
    run_with_timeout,
)
from .format_parser import FormatParser, ParsedData
from .unicode_armor import detect_unicode_spoofing, preprocess_for_pii_detection, unicode_armor

__all__ = [
    "APXVRedactionEngine",
    "APXRedactionEngine",
    "RedactionBackendRegistry",
    "REDACTION_ENGINE_VERSION",
    "FormatParser",
    "ParsedData",
    "deep_redact_with_count",
    "run_with_timeout",
    "detect_unicode_spoofing",
    "preprocess_for_pii_detection",
    "unicode_armor",
]