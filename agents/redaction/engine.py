"""APX RedactionEngine v3 — pattern-based PII redaction with entity tracking."""

from __future__ import annotations

import concurrent.futures
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, TypeVar

from .backends import RedactionBackendRegistry
from .format_parser import FormatParser
from .patterns import PIIPattern, compile_patterns
from .unicode_armor import preprocess_for_pii_detection, unicode_armor

T = TypeVar("T")

REDACTION_ENGINE_VERSION = "3.0.0"
MAX_TEXT_LENGTH = 500_000
REDACTION_TIMEOUT_SECONDS = 8
NAME_FLAG_PHRASE = "redact personal names"

PLACEHOLDER_PATTERN = re.compile(r"\[REDACTED(?:-[A-Z0-9]+)+\]")

LEGACY_CATEGORY_ORDER = ("EMAIL", "PHONE", "SSN", "CC", "NAME")

TYPE_TO_LEGACY = {
    "email_address": "EMAIL",
    "phone_number": "PHONE",
    "fax_number": "PHONE",
    "ssn": "SSN",
    "ssn_last4": "SSN",
    "ssn_fragment": "SSN",
    "credit_card": "CC",
    "credit_card_dashed": "CC",
    "credit_card_generic": "CC",
    "cc_fragment": "CC",
    "cvv": "CC",
    "full_name": "NAME",
    "uppercase_name": "NAME",
    "name_after_title": "NAME",
    "titled_name_postprocess": "NAME",
    "name_orphan_bridge": "NAME",
    "embedded_name_date_postprocess": "NAME",
    "ner_name": "NAME",
    "name_with_credential": "NAME",
    "lowercase_name_credential": "NAME",
    "concatenated_name_suffix": "NAME",
    "embedded_name_date": "NAME",
}


@dataclass
class PIIEntity:
    type: str
    value: str
    start: int
    end: int
    severity: str
    category: str
    redacted_as: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "value": self.value,
            "start": self.start,
            "end": self.end,
            "severity": self.severity,
            "category": self.category,
            "redacted_as": self.redacted_as,
        }


@dataclass
class RedactionSummary:
    total_detected: int = 0
    by_category: Dict[str, int] = field(default_factory=dict)
    by_severity: Dict[str, int] = field(default_factory=dict)


def _luhn_valid(number: str) -> bool:
    digits = [int(ch) for ch in number if ch.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _ssn_parts_valid(area: str, group: str, serial: str) -> bool:
    if area in {"000", "666"} or group == "00" or serial == "0000":
        return False
    return True


def _digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def _legacy_category(entity_type: str) -> Optional[str]:
    if entity_type in TYPE_TO_LEGACY:
        return TYPE_TO_LEGACY[entity_type]
    lowered = entity_type.lower()
    if "email" in lowered:
        return "EMAIL"
    if "phone" in lowered or "fax" in lowered:
        return "PHONE"
    if "ssn" in lowered:
        return "SSN"
    if "credit" in lowered or lowered == "cvv" or "cc_" in lowered:
        return "CC"
    if "name" in lowered:
        return "NAME"
    return None


def run_with_timeout(
    func: Callable[[], T],
    seconds: float,
    error_msg: str = "Operation timed out",
) -> T:
    """Run func with a wall-clock timeout (portable; supports sub-second limits)."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=seconds)
        except concurrent.futures.TimeoutError as exc:
            raise TimeoutError(error_msg) from exc


class APXVRedactionEngine:
    """Expanded redaction engine with entity output for downstream attestation."""

    def __init__(self, audit_logger: Any = None) -> None:
        self._patterns: Optional[List[PIIPattern]] = None
        self._backends = RedactionBackendRegistry()
        self._audit_logger = audit_logger

    def register_backend(self, name: str, handler: Callable[..., Dict[str, Any]]) -> str:
        """Register a BYO redaction backend. Returns stable backend_id."""
        return self._backends.register(name, handler)

    def list_backends(self) -> List[str]:
        return self._backends.list_ids()

    def _normalize_backend_result(
        self,
        raw: Dict[str, Any],
        *,
        input_format: str,
    ) -> Dict[str, Any]:
        entities = raw.get("entities", [])
        legacy_counts = {key: 0 for key in LEGACY_CATEGORY_ORDER}
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            legacy = _legacy_category(entity.get("type", ""))
            if legacy:
                legacy_counts[legacy] += 1

        redactions_applied = raw.get("redactions_applied")
        if not isinstance(redactions_applied, list):
            redactions_applied = [
                {"category": category, "count": legacy_counts[category]}
                for category in LEGACY_CATEGORY_ORDER
                if legacy_counts[category] > 0
            ]

        total = raw.get("total_redactions")
        if not isinstance(total, int):
            total = sum(legacy_counts.values())

        summary = (
            "No redactions applied per APXV-RULE-001."
            if total == 0
            else f"Applied {total} redaction(s) via backend {raw.get('backend_id', 'unknown')}."
        )

        return {
            "redacted_text": raw["redacted_text"],
            "redactions_applied": redactions_applied,
            "total_redactions": total,
            "engine_version": REDACTION_ENGINE_VERSION,
            "redaction_summary": summary,
            "uncertain_matches": raw.get("uncertain_matches", []),
            "entities": entities,
            "entity_count": len(entities),
            "input_format": input_format,
            "redaction_backend_id": raw.get("backend_id"),
            "redaction_input_hash": raw.get("input_hash"),
        }

    def _apply_via_backend(self, text: str, backend_id: str) -> Dict[str, Any]:
        parser = FormatParser()
        parsed = parser.parse(text)
        fmt = parsed.original_format
        raw = self._backends.invoke(backend_id, text=text, input_format=fmt)
        result = self._normalize_backend_result(raw, input_format=fmt)

        if self._audit_logger is not None:
            self._audit_logger.log_event(
                "redaction_backend_invoked",
                {
                    "backend_id": backend_id,
                    "input_hash": raw.get("input_hash"),
                    "input_format": fmt,
                    "entity_count": result.get("entity_count", 0),
                    "total_redactions": result.get("total_redactions", 0),
                },
            )
        return result

    def _get_patterns(self, *, redact_names: bool) -> List[PIIPattern]:
        return compile_patterns(include_names=redact_names)

    def redact_pii(self, text: str, *, redact_names: bool = False) -> Dict[str, Any]:
        if not isinstance(text, str):
            raise TypeError("redact_pii: input must be a string")
        if len(text) > MAX_TEXT_LENGTH:
            raise ValueError(
                f"redact_pii: input too large ({len(text):,} chars). "
                f"Maximum is {MAX_TEXT_LENGTH:,} chars."
            )
        return run_with_timeout(
            lambda: self._redact_pii_impl(text, redact_names=redact_names),
            REDACTION_TIMEOUT_SECONDS,
            "Redaction timeout: input may be too complex",
        )

    def _redact_pii_impl(self, text: str, *, redact_names: bool = False) -> Dict[str, Any]:
        normalized = unicode_armor(text)
        normalized = re.sub(r"\s+", " ", normalized) if normalized else normalized
        redacted = normalized
        entities: List[PIIEntity] = []
        summary = RedactionSummary()
        uncertain: List[Dict[str, Any]] = []

        for pattern in self._get_patterns(redact_names=redact_names):
            if not self._pattern_applies(pattern, redacted):
                continue
            matches = list(pattern.regex.finditer(redacted))
            for match in reversed(matches):
                matched = match.group(0)
                start, end = match.start(), match.end()
                if not self._accept_match(pattern, matched, redacted, start, uncertain):
                    continue
                replacement = self._replacement_for_match(pattern, matched)
                entities.append(
                    PIIEntity(
                        type=pattern.type,
                        value=matched,
                        start=start,
                        end=end,
                        severity=pattern.severity,
                        category=pattern.category,
                        redacted_as=replacement,
                    )
                )
                redacted = redacted[:start] + replacement + redacted[end:]
                summary.total_detected += 1
                summary.by_category[pattern.category] = (
                    summary.by_category.get(pattern.category, 0) + 1
                )
                summary.by_severity[pattern.severity] = (
                    summary.by_severity.get(pattern.severity, 0) + 1
                )

        redacted, entities, summary, uncertain = self._apply_legacy_supplements(
            redacted, entities, summary, uncertain
        )
        redacted, entities, summary = self._post_process(
            redacted, entities, summary, redact_names
        )

        return {
            "redacted_text": redacted,
            "entities": [entity.as_dict() for entity in entities],
            "summary": {
                "total_detected": summary.total_detected,
                "by_category": summary.by_category,
                "by_severity": summary.by_severity,
            },
            "uncertain_matches": uncertain,
        }

    def _replacement_for_match(self, pattern: PIIPattern, matched: str) -> str:
        replacement = pattern.replacement
        if "\\" in replacement:
            return pattern.regex.sub(replacement, matched, count=1)
        return replacement

    def _pattern_applies(self, pattern: PIIPattern, text: str) -> bool:
        return True

    def _accept_match(
        self,
        pattern: PIIPattern,
        matched: str,
        text: str,
        start: int,
        uncertain: List[Dict[str, Any]],
    ) -> bool:
        if pattern.type == "national_id_numbers":
            prefix = text[max(0, start - 24) : start].lower()
            if re.search(r"routing[\s:#]+$", prefix):
                return False
        if pattern.type == "address":
            prefix = text[max(0, start - 4) : start]
            if re.search(r"\d{1,2}\.$", prefix):
                return False
        if pattern.type == "phone_number":
            prefix = text[max(0, start - 20) : start].lower()
            if re.search(r"(?:fax|facsimile|f:)\s*$", prefix):
                return False
        if pattern.type == "bare_domain_url":
            prefix = text[max(0, start - 12) : start]
            if prefix.endswith("@") or "://" in prefix or prefix.endswith("www."):
                return False
        if pattern.type == "date_of_birth":
            context = text[max(0, start - 16) : start + len(matched)].lower()
            contextual = bool(re.search(r"\b(?:dob|born|birth)\b", context))
            if re.search(r"\d{1,2}/\d{1,2}/\d{2,4}", matched) and not contextual:
                return False
            if re.search(r"\d{4}-\d{1,2}-\d{1,2}", matched) and not contextual:
                return False
        if pattern.type in {"any_date_slash", "any_date_dash"}:
            prefix = text[max(0, start - 12) : start].lower()
            if re.search(r"\b(?:dob|born|birth|partial)\s*:?\s*$", prefix):
                return False
        if pattern.type == "date_spelled_month_noyear":
            prefix = text[max(0, start - 16) : start].lower()
            if re.search(r"\b(?:dob|born|birth|partial)\b", prefix):
                return False
        if pattern.type == "bank_account":
            if _luhn_valid(_digits_only(matched)):
                uncertain.append(
                    {
                        "category": "CC",
                        "text": matched,
                        "reason": "luhn_valid_credit_card",
                        "type": pattern.type,
                    }
                )
                return False
        if pattern.type in {"credit_card", "credit_card_generic", "credit_card_dashed"}:
            if not _luhn_valid(_digits_only(matched)):
                uncertain.append(
                    {"category": "CC", "text": matched, "reason": "luhn_failed", "type": pattern.type}
                )
                return False
        if pattern.type == "ssn":
            dashed = re.search(r"(\d{3})-(\d{2})-(\d{4})", matched)
            if dashed and not _ssn_parts_valid(*dashed.groups()):
                uncertain.append(
                    {"category": "SSN", "text": matched, "reason": "invalid_ssn_range", "type": pattern.type}
                )
                return False
        if pattern.type == "email_address":
            if "." not in matched.split("@", 1)[-1]:
                uncertain.append(
                    {"category": "EMAIL", "text": matched, "reason": "invalid_domain", "type": pattern.type}
                )
                return False
        return True

    def _apply_legacy_supplements(
        self,
        text: str,
        entities: List[PIIEntity],
        summary: RedactionSummary,
        uncertain: List[Dict[str, Any]],
    ) -> Tuple[str, List[PIIEntity], RedactionSummary, List[Dict[str, Any]]]:
        redacted = text
        contextual_ssn = re.compile(
            r"(?:SSN|Social Security(?: Number)?)\s*:?\s*(\d{3}-\d{2}-\d{4}|\d{9})",
            re.IGNORECASE,
        )
        for match in contextual_ssn.finditer(redacted):
            token = match.group(1)
            if "-" in token:
                area, group, serial = token.split("-")
                if not _ssn_parts_valid(area, group, serial):
                    uncertain.append(
                        {"category": "SSN", "text": token, "reason": "invalid_ssn_range", "type": "ssn"}
                    )
                    continue
            elif len(token) != 9 or not token.isdigit():
                continue
            else:
                area, group, serial = token[:3], token[3:5], token[5:]
                if not _ssn_parts_valid(area, group, serial):
                    continue
            start, end = match.start(1), match.end(1)
            entities.append(
                PIIEntity(
                    type="ssn",
                    value=token,
                    start=start,
                    end=end,
                    severity="critical",
                    category="Financial Information",
                    redacted_as="[REDACTED-SSN]",
                )
            )
            redacted = redacted[:start] + "[REDACTED-SSN]" + redacted[end:]
            summary.total_detected += 1
            summary.by_category["Financial Information"] = (
                summary.by_category.get("Financial Information", 0) + 1
            )
            summary.by_severity["critical"] = summary.by_severity.get("critical", 0) + 1

        cc_candidate = re.compile(r"\b(?:\d[-\s]?){12,18}\d\b")
        for match in list(cc_candidate.finditer(redacted)):
            matched = match.group(0)
            if not _luhn_valid(_digits_only(matched)):
                uncertain.append({"category": "CC", "text": matched, "reason": "luhn_failed", "type": "credit_card"})
                continue
            if "[REDACTED-CC]" in matched:
                continue
            start, end = match.start(), match.end()
            entities.append(
                PIIEntity(
                    type="credit_card",
                    value=matched,
                    start=start,
                    end=end,
                    severity="critical",
                    category="Financial Information",
                    redacted_as="[REDACTED-CC]",
                )
            )
            redacted = redacted[:start] + "[REDACTED-CC]" + redacted[end:]
            summary.total_detected += 1
            summary.by_category["Financial Information"] = (
                summary.by_category.get("Financial Information", 0) + 1
            )
            summary.by_severity["critical"] = summary.by_severity.get("critical", 0) + 1

        return redacted, entities, summary, uncertain

    def _post_process(
        self,
        text: str,
        entities: List[PIIEntity],
        summary: RedactionSummary,
        redact_names: bool,
    ) -> Tuple[str, List[PIIEntity], RedactionSummary]:
        redacted = text

        def post_replace(
            pattern: re.Pattern[str],
            token: str,
            entity_type: str,
            category: str = "Personal Information",
            severity: str = "high",
        ) -> None:
            nonlocal redacted

            def replacer(match: re.Match[str]) -> str:
                matched = match.group(0)
                entities.append(
                    PIIEntity(
                        type=entity_type,
                        value=matched,
                        start=-1,
                        end=-1,
                        severity=severity,
                        category=category,
                        redacted_as=token,
                    )
                )
                summary.total_detected += 1
                summary.by_category[category] = summary.by_category.get(category, 0) + 1
                summary.by_severity[severity] = summary.by_severity.get(severity, 0) + 1
                return token

            redacted = pattern.sub(replacer, redacted)

        orphan_bridge = re.compile(
            r"\b([A-Z][a-z]+)\s+(\[REDACTED(?:-[A-Z0-9]+)+\])\s+([A-Z][a-z]+)\b"
        )

        def orphan_replacer(match: re.Match[str]) -> str:
            full_match = match.group(0)
            entities.append(
                PIIEntity(
                    type="name_orphan_bridge",
                    value=full_match,
                    start=-1,
                    end=-1,
                    severity="critical",
                    category="Personal Information",
                    redacted_as="[REDACTED-NAME]",
                )
            )
            summary.total_detected += 1
            summary.by_category["Personal Information"] = (
                summary.by_category.get("Personal Information", 0) + 1
            )
            summary.by_severity["critical"] = summary.by_severity.get("critical", 0) + 1
            return "[REDACTED-NAME]"

        redacted = orphan_bridge.sub(orphan_replacer, redacted)

        if redact_names:
            post_replace(
                re.compile(
                    r"\b(?:Dr\.|Doctor|Prof\.|Professor|Rev\.|Hon\.)\s+"
                    r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
                ),
                "[REDACTED-NAME]",
                "titled_name_postprocess",
                severity="critical",
            )
            post_replace(
                re.compile(
                    r"\b(?:Dr\.?|Doctor|Prof\.?|Professor|Rev\.?|Hon\.?)\s+"
                    r"(?=\[REDACTED-NAME\])",
                    re.IGNORECASE,
                ),
                "",
                "titled_orphan_remove_postprocess",
                severity="critical",
            )
            post_replace(
                re.compile(
                    r"\b[A-Z][a-z]{1,30}(?:\s+[A-Z][a-z]{1,30}){1,3}\b"
                ),
                "[REDACTED-NAME]",
                "full_name",
                severity="high",
            )

        post_replace(
            re.compile(
                r"\b([a-z]{2,})(?:pon|on)?\d{1,2}"
                r"(?:january|february|march|april|may|june|july|august|"
                r"september|october|november|december)\b",
                re.IGNORECASE,
            ),
            "[REDACTED-NAME-DATE]",
            "embedded_name_date_postprocess",
            severity="critical",
        )
        post_replace(
            re.compile(
                r"\[REDACTED-AGE\]\s+(?:male|female|m(?:ales?)?|f(?:emales?)?)\b",
                re.IGNORECASE,
            ),
            "[REDACTED-AGE] [REDACTED-SEX]",
            "age_sex_postprocess",
            "Demographics",
            "critical",
        )
        post_replace(
            re.compile(
                r"(?:[a-z]+)?(?:a)?(\d{1,3})(?:yo|y\.o\.|y/o)"
                r"(?:male|female|m(?:ales?)?|f(?:emales?)?)",
                re.IGNORECASE,
            ),
            "[REDACTED-AGE] [REDACTED-SEX]",
            "age_sex_compact_postprocess",
            "Demographics",
            "critical",
        )
        post_replace(
            re.compile(
                r"\b\d{1,2}\s*(?:january|february|march|april|may|june|july|"
                r"august|september|october|november|december)\b",
                re.IGNORECASE,
            ),
            "[REDACTED-DATE]",
            "date_day_month_postprocess",
            severity="critical",
        )

        return redacted, entities, summary

    def apply(
        self,
        text: str,
        *,
        redact_names: bool = False,
        backend_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if backend_id:
            return self._apply_via_backend(text, backend_id)

        if NAME_FLAG_PHRASE in text.lower():
            redact_names = True

        parser = FormatParser()
        parsed = parser.parse(text)
        fmt = parsed.original_format

        if fmt == "text":
            return self._apply_text_segments(text, redact_names=redact_names)

        deep_result = deep_redact_with_count(
            parsed.data, self, redact_names=redact_names
        )
        redacted_text = parser.serialize(deep_result["redacted"], fmt)
        all_entities = deep_result["entities"]
        uncertain: List[Dict[str, Any]] = []
        legacy_counts = {key: 0 for key in LEGACY_CATEGORY_ORDER}
        for entity in all_entities:
            legacy = _legacy_category(entity["type"])
            if legacy:
                legacy_counts[legacy] += 1

        redactions_applied = [
            {"category": category, "count": legacy_counts[category]}
            for category in LEGACY_CATEGORY_ORDER
            if legacy_counts[category] > 0
        ]
        total = sum(legacy_counts.values())
        summary = (
            "No redactions applied per APXV-RULE-001."
            if total == 0
            else f"Applied {total} redaction(s) across {len(redactions_applied)} categories."
        )

        return {
            "redacted_text": redacted_text,
            "redactions_applied": redactions_applied,
            "total_redactions": total,
            "engine_version": REDACTION_ENGINE_VERSION,
            "redaction_summary": summary,
            "uncertain_matches": uncertain,
            "entities": all_entities,
            "entity_count": len(all_entities),
            "input_format": fmt,
        }

    def _apply_text_segments(self, text: str, *, redact_names: bool) -> Dict[str, Any]:
        segments = self._split_segments(text)
        rebuilt: List[str] = []
        all_entities: List[Dict[str, Any]] = []
        uncertain: List[Dict[str, Any]] = []
        legacy_counts = {key: 0 for key in LEGACY_CATEGORY_ORDER}

        for kind, segment in segments:
            if kind == "placeholder":
                rebuilt.append(segment)
                continue
            result = self.redact_pii(segment, redact_names=redact_names)
            rebuilt.append(result["redacted_text"])
            all_entities.extend(result["entities"])
            uncertain.extend(result["uncertain_matches"])
            for entity in result["entities"]:
                legacy = _legacy_category(entity["type"])
                if legacy:
                    legacy_counts[legacy] += 1

        redactions_applied = [
            {"category": category, "count": legacy_counts[category]}
            for category in LEGACY_CATEGORY_ORDER
            if legacy_counts[category] > 0
        ]
        total = sum(legacy_counts.values())
        summary = (
            "No redactions applied per APXV-RULE-001."
            if total == 0
            else f"Applied {total} redaction(s) across {len(redactions_applied)} categories."
        )

        return {
            "redacted_text": "".join(rebuilt),
            "redactions_applied": redactions_applied,
            "total_redactions": total,
            "engine_version": REDACTION_ENGINE_VERSION,
            "redaction_summary": summary,
            "uncertain_matches": uncertain,
            "entities": all_entities,
            "entity_count": len(all_entities),
            "input_format": "text",
        }

    def _split_segments(self, text: str) -> List[Tuple[str, str]]:
        segments: List[Tuple[str, str]] = []
        cursor = 0
        for match in PLACEHOLDER_PATTERN.finditer(text):
            if match.start() > cursor:
                segments.append(("text", text[cursor : match.start()]))
            segments.append(("placeholder", match.group()))
            cursor = match.end()
        if cursor < len(text):
            segments.append(("text", text[cursor:]))
        if not segments:
            segments.append(("text", text))
        return segments


def deep_redact_with_count(
    value: Any,
    engine: Optional[APXVRedactionEngine] = None,
    *,
    redact_names: bool = False,
) -> Dict[str, Any]:
    engine = engine or APXVRedactionEngine()
    entities: List[Dict[str, Any]] = []
    detections = 0

    def walk(item: Any) -> Any:
        nonlocal detections
        if isinstance(item, str):
            armored = preprocess_for_pii_detection(item)
            if isinstance(armored, str):
                result = engine.redact_pii(armored, redact_names=redact_names)
                detections += result["summary"]["total_detected"]
                entities.extend(result["entities"])
                return result["redacted_text"]
            return armored
        if isinstance(item, list):
            return [walk(child) for child in item]
        if isinstance(item, dict):
            return {key: walk(child) for key, child in item.items()}
        return item

    return {"redacted": walk(value), "detections": detections, "entities": entities}


# v1.3.x compat alias — removed in v1.4
APXRedactionEngine = APXVRedactionEngine