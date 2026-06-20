"""Per-pattern regression catalog — one professional test case per compiled pattern."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.redaction import APXRedactionEngine
from agents.redaction.patterns import compile_patterns
from tests.fixtures.pattern_catalog import PATTERN_PROBES, PatternProbe

ENGINE = APXRedactionEngine()
COMPILED_TYPES = {p.type for p in compile_patterns()}
CATALOG_TYPES = {probe.pattern_type for probe in PATTERN_PROBES}


def test_catalog_covers_every_compiled_pattern():
    missing = sorted(COMPILED_TYPES - CATALOG_TYPES)
    extra = sorted(CATALOG_TYPES - COMPILED_TYPES)
    assert not missing, f"Catalog missing probes for: {missing}"
    assert not extra, f"Catalog has probes for non-compiled patterns: {extra}"
    assert len(PATTERN_PROBES) == len(COMPILED_TYPES) == 68


@pytest.mark.parametrize(
    "probe",
    PATTERN_PROBES,
    ids=[probe.pattern_type for probe in PATTERN_PROBES],
)
def test_pattern_redacts_secret_and_fires(probe: PatternProbe):
    result = ENGINE.redact_pii(probe.input_text)
    entity_types = {entity["type"] for entity in result["entities"]}

    assert probe.secret not in result["redacted_text"], (
        f"{probe.pattern_type}: secret '{probe.secret}' still in output: "
        f"{result['redacted_text']!r}"
    )
    expected = {probe.pattern_type, *probe.also_accepts}
    assert entity_types & expected, (
        f"{probe.pattern_type}: expected one of {sorted(expected)}; got {sorted(entity_types)} "
        f"from input {probe.input_text!r}"
    )
    assert result["summary"]["total_detected"] >= 1


@pytest.mark.parametrize(
    "probe",
    PATTERN_PROBES,
    ids=[f"regex:{probe.pattern_type}" for probe in PATTERN_PROBES],
)
def test_pattern_regex_matches_probe(probe: PatternProbe):
    """Unit-level: the compiled regex itself must match the catalog input."""
    compiled = {p.type: p for p in compile_patterns()}
    pattern = compiled[probe.pattern_type]
    assert pattern.regex.search(probe.input_text), (
        f"{probe.pattern_type}: regex did not match catalog input {probe.input_text!r}"
    )