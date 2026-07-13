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

# Lower value = runs earlier (more specific patterns beat broad fallbacks).
EXECUTION_PRIORITY: dict[str, int] = {
    "email_address": 2,
    "web_url": 3,
    "fax_number": 4,
    "credit_card_dashed": 6,
    "credit_card": 7,
    "credit_card_generic": 8,
    "cc_fragment": 9,
    "city_state_zip_pattern": 10,
    "city_state_pattern": 11,
    "po_box": 12,
    "uppercase_name": 12,
    "person_full_name": 13,
    "full_name": 14,
    "age_sex_combo": 16,
    "month_abbrev_in_context": 16,
    "date_spelled_month_with_year": 17,
    "date_spelled_month_day_first": 18,
    "date_spelled_month_noyear": 19,
    "any_date_slash": 20,
    "any_date_dash": 21,
    "partial_dob": 22,
    "date_of_birth": 23,
    "birth_year": 25,
    "name_with_credential": 26,
    "lowercase_name_credential": 27,
    "ssn": 23,
    "ssn_fragment": 24,
    "ssn_last4": 25,
    "standalone_alphanumeric_id": 28,
    "device_serial_number": 29,
    "city_county_names": 30,
    "phone_number": 40,
    "bare_domain_url": 45,
    "date_dash_mdy": 48,
    "bank_account": 55,
    "age_pattern": 56,
    "age_prefix": 57,
    "age_compressed": 58,
}


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
    compiled.sort(key=lambda p: (EXECUTION_PRIORITY.get(p.type, 25), p.type))
    return compiled