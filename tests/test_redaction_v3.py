"""Tests for APX RedactionEngine v3."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.redaction import APXRedactionEngine
from agents.redaction.patterns_data import PATTERN_COUNT

ENGINE = APXRedactionEngine()


def test_pattern_count_loaded():
    assert PATTERN_COUNT >= 60


def test_redacts_ssn_and_emits_entities():
    result = ENGINE.redact_pii("SSN: 123-45-6789")
    assert "123-45-6789" not in result["redacted_text"]
    assert result["summary"]["total_detected"] >= 1
    assert result["entities"]


def test_redacts_email():
    result = ENGINE.redact_pii("Contact: john.doe@example.com for details.")
    assert "john.doe@example.com" not in result["redacted_text"]


def test_redacts_credit_card():
    result = ENGINE.redact_pii("Card: 4111111111111111")
    assert "4111111111111111" not in result["redacted_text"]


def test_no_pii_unchanged():
    text = "The weather today is sunny and warm."
    result = ENGINE.redact_pii(text)
    assert result["redacted_text"] == text
    assert result["summary"]["total_detected"] == 0


def test_rejects_oversized_input():
    with pytest.raises(ValueError, match="too large"):
        ENGINE.redact_pii("x" * 600_000)


def test_apply_includes_entity_count():
    result = ENGINE.apply(
        "Contact john.doe@example.com or call (555) 123-4567. SSN: 123-45-6789."
    )
    assert result["entity_count"] == len(result["entities"])
    assert result["entity_count"] >= 2