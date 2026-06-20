"""Compiled regex patterns for APXRedactionEngine."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Sequence

from .patterns_data import PATTERN_DEFINITIONS
from .patterns_supplement import SUPPLEMENTAL_PATTERN_DEFINITIONS

ALL_PATTERN_DEFINITIONS = [*PATTERN_DEFINITIONS, *SUPPLEMENTAL_PATTERN_DEFINITIONS]


@dataclass(frozen=True)
class PIIPattern:
    category: str
    type: str
    regex: re.Pattern[str]
    replacement: str
    description: str
    severity: str
    enabled: bool


DISABLED_PATTERN_TYPES = frozenset(
    {
        "standalone_number_20_digits",
        "standalone_number_12_digits",
        "standalone_number_10_digits",
        "standalone_number_9_digits",
        "standalone_number_8_digits",
        "standalone_number_7_digits",
        "standalone_number_6_digits",
    }
)

# Broad name sweeps are post-process only (gated by redact_names in engine).
# Keyword-anchored name patterns always compile and run.
NAME_PATTERN_TYPES = frozenset()


def compile_patterns(
    definitions: Sequence[dict] = ALL_PATTERN_DEFINITIONS,
    *,
    include_names: bool = False,
) -> List[PIIPattern]:
    compiled: List[PIIPattern] = []
    for item in definitions:
        if not item.get("enabled", True):
            continue
        ptype = item["type"]
        if ptype in DISABLED_PATTERN_TYPES:
            continue
        if not include_names and ptype in NAME_PATTERN_TYPES:
            continue
        flags = item.get("flags", 0)
        try:
            compiled_regex = re.compile(item["regex"], flags)
        except re.error:
            # Skip patterns using JS-only or variable-width lookbehind unsupported in Python.
            continue
        compiled.append(
            PIIPattern(
                category=item["category"],
                type=ptype,
                regex=compiled_regex,
                replacement=item["replacement"],
                description=item["description"],
                severity=item["severity"],
                enabled=True,
            )
        )
    return compiled