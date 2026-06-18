"""
APX v1 — Production Redaction Engine (Phase 4 / Step 5)

Deterministic PII redaction per APX-RULE-001 with validation, ordering,
and placeholder preservation. Stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple
import re

REDACTION_ENGINE_VERSION = "2.0.0"

PLACEHOLDER_PATTERN = re.compile(r"\[REDACTED-(?:EMAIL|PHONE|SSN|CC|NAME)\]")
NAME_FLAG_PHRASE = "redact personal names"

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9](?:[A-Za-z0-9._%+-]{0,62}[A-Za-z0-9])?"
    r"@[A-Za-z0-9](?:[A-Za-z0-9.-]{0,62}[A-Za-z0-9])?"
    r"\.[A-Za-z]{2,24}\b"
)

PHONE_PATTERNS = (
    re.compile(
        r"(?<!\d)(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)"
    ),
    re.compile(r"(?<!\d)\+\d{1,3}[-.\s]?\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}(?!\d)"),
)

SSN_DASHED_PATTERN = re.compile(r"\b(\d{3})-(\d{2})-(\d{4})\b")
SSN_CONTEXT_PATTERN = re.compile(
    r"(?:SSN|Social Security(?: Number)?)\s*:?\s*(\d{3}-\d{2}-\d{4}|\d{9})",
    re.IGNORECASE,
)

CC_CANDIDATE_PATTERN = re.compile(
    r"\b(?:\d[-\s]?){12,18}\d\b"
)

NAME_PATTERN = re.compile(
    r"\b[A-Z][a-z]{1,30}(?:\s+[A-Z][a-z]{1,30}){1,3}\b"
)


@dataclass
class RedactionMatch:
    start: int
    end: int
    category: str
    replacement: str
    matched_text: str


@dataclass
class RedactionResult:
    redacted_text: str
    redactions_applied: List[Dict[str, Any]] = field(default_factory=list)
    total_redactions: int = 0
    engine_version: str = REDACTION_ENGINE_VERSION
    redaction_summary: str = ""
    uncertain_matches: List[Dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "redacted_text": self.redacted_text,
            "redactions_applied": self.redactions_applied,
            "total_redactions": self.total_redactions,
            "engine_version": self.engine_version,
            "redaction_summary": self.redaction_summary,
            "uncertain_matches": self.uncertain_matches,
        }


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
    if area == "000" or area == "666":
        return False
    if group == "00":
        return False
    if serial == "0000":
        return False
    return True


def _digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def _split_segments(text: str) -> List[Tuple[str, str]]:
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


def _apply_matches(text: str, matches: Sequence[RedactionMatch]) -> str:
    if not matches:
        return text
    ordered = sorted(matches, key=lambda item: item.start, reverse=True)
    redacted = text
    for match in ordered:
        redacted = redacted[: match.start] + match.replacement + redacted[match.end :]
    return redacted


def _non_overlapping(matches: List[RedactionMatch]) -> List[RedactionMatch]:
    if not matches:
        return []
    ordered = sorted(matches, key=lambda item: (item.start, -(item.end - item.start)))
    kept: List[RedactionMatch] = []
    last_end = -1
    for match in ordered:
        if match.start < last_end:
            continue
        kept.append(match)
        last_end = match.end
    return kept


class RedactionEngine:
    """Deterministic governed redaction engine for APX-RULE-001."""

    CATEGORY_ORDER = ("EMAIL", "PHONE", "SSN", "CC", "NAME")

    def apply(self, text: str, *, redact_names: bool = False) -> Dict[str, Any]:
        if NAME_FLAG_PHRASE in text.lower():
            redact_names = True

        segments = _split_segments(text)
        rebuilt_segments: List[str] = []
        category_counts: Dict[str, int] = {key: 0 for key in self.CATEGORY_ORDER}
        uncertain: List[Dict[str, Any]] = []

        for kind, segment in segments:
            if kind == "placeholder":
                rebuilt_segments.append(segment)
                continue

            redacted_segment, counts, notes = self._redact_segment(
                segment,
                redact_names=redact_names,
            )
            rebuilt_segments.append(redacted_segment)
            for category, count in counts.items():
                category_counts[category] += count
            uncertain.extend(notes)

        redactions_applied = [
            {"category": category, "count": category_counts[category]}
            for category in self.CATEGORY_ORDER
            if category_counts[category] > 0
        ]
        total = sum(category_counts.values())
        summary = (
            "No redactions applied per APX-RULE-001."
            if total == 0
            else f"Applied {total} redaction(s) across {len(redactions_applied)} categories."
        )

        return RedactionResult(
            redacted_text="".join(rebuilt_segments),
            redactions_applied=redactions_applied,
            total_redactions=total,
            redaction_summary=summary,
            uncertain_matches=uncertain,
        ).as_dict()

    def _redact_segment(
        self,
        text: str,
        *,
        redact_names: bool,
    ) -> Tuple[str, Dict[str, int], List[Dict[str, Any]]]:
        matches: List[RedactionMatch] = []
        uncertain: List[Dict[str, Any]] = []

        for match in EMAIL_PATTERN.finditer(text):
            if "." not in match.group().split("@", 1)[-1]:
                uncertain.append({"category": "EMAIL", "text": match.group(), "reason": "invalid_domain"})
                continue
            matches.append(
                RedactionMatch(
                    start=match.start(),
                    end=match.end(),
                    category="EMAIL",
                    replacement="[REDACTED-EMAIL]",
                    matched_text=match.group(),
                )
            )

        for pattern in PHONE_PATTERNS:
            for match in pattern.finditer(text):
                digits = _digits_only(match.group())
                if len(digits) < 10 or len(digits) > 15:
                    continue
                matches.append(
                    RedactionMatch(
                        start=match.start(),
                        end=match.end(),
                        category="PHONE",
                        replacement="[REDACTED-PHONE]",
                        matched_text=match.group(),
                    )
                )

        for match in SSN_DASHED_PATTERN.finditer(text):
            area, group, serial = match.group(1), match.group(2), match.group(3)
            if not _ssn_parts_valid(area, group, serial):
                uncertain.append(
                    {"category": "SSN", "text": match.group(), "reason": "invalid_ssn_range"}
                )
                continue
            matches.append(
                RedactionMatch(
                    start=match.start(),
                    end=match.end(),
                    category="SSN",
                    replacement="[REDACTED-SSN]",
                    matched_text=match.group(),
                )
            )

        for match in SSN_CONTEXT_PATTERN.finditer(text):
            token = match.group(1)
            if "-" in token:
                continue
            if len(token) != 9 or not token.isdigit():
                continue
            area, group, serial = token[:3], token[3:5], token[5:]
            if not _ssn_parts_valid(area, group, serial):
                continue
            start = match.start(1)
            end = match.end(1)
            matches.append(
                RedactionMatch(
                    start=start,
                    end=end,
                    category="SSN",
                    replacement="[REDACTED-SSN]",
                    matched_text=token,
                )
            )

        for match in CC_CANDIDATE_PATTERN.finditer(text):
            digits = _digits_only(match.group())
            if not _luhn_valid(digits):
                uncertain.append(
                    {"category": "CC", "text": match.group(), "reason": "luhn_failed"}
                )
                continue
            matches.append(
                RedactionMatch(
                    start=match.start(),
                    end=match.end(),
                    category="CC",
                    replacement="[REDACTED-CC]",
                    matched_text=match.group(),
                )
            )

        if redact_names:
            for match in NAME_PATTERN.finditer(text):
                matches.append(
                    RedactionMatch(
                        start=match.start(),
                        end=match.end(),
                        category="NAME",
                        replacement="[REDACTED-NAME]",
                        matched_text=match.group(),
                    )
                )

        filtered = _non_overlapping(matches)
        counts: Dict[str, int] = {key: 0 for key in self.CATEGORY_ORDER}
        for match in filtered:
            counts[match.category] += 1

        return _apply_matches(text, filtered), counts, uncertain