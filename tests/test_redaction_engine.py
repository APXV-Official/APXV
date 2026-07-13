"""Tests for production redaction engine (Phase 4 Step 5)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.redaction_engine import RedactionEngine, _luhn_valid

ENGINE = RedactionEngine()
SAMPLE_INPUT = (
    "Contact John at john.doe@example.com or call (555) 123-4567. "
    "SSN: 123-45-6789. Card: 4111 1111 1111 1111."
)


def test_sample_input_redacts_four_categories():
    result = ENGINE.apply(SAMPLE_INPUT)
    assert result["total_redactions"] == 4
    assert "[REDACTED-EMAIL]" in result["redacted_text"]
    assert "[REDACTED-PHONE]" in result["redacted_text"]
    assert "[REDACTED-SSN]" in result["redacted_text"]
    assert "[REDACTED-CC]" in result["redacted_text"]


def test_no_sensitive_data_summary():
    result = ENGINE.apply("Hello world, nothing sensitive here.")
    assert result["total_redactions"] == 0
    assert result["redaction_summary"] == "No redactions applied per APXV-RULE-001."


def test_luhn_rejects_invalid_card():
    assert _luhn_valid("4111111111111111") is True
    assert _luhn_valid("1234567890123456") is False
    result = ENGINE.apply("Card 1234 5678 9012 3456 only")
    assert "[REDACTED-CC]" not in result["redacted_text"]
    assert any(note["reason"] == "luhn_failed" for note in result["uncertain_matches"])


def test_international_phone_redacted():
    result = ENGINE.apply("Reach us at +44 20 7946 0958 today.")
    assert "[REDACTED-PHONE]" in result["redacted_text"]


def test_existing_placeholders_preserved():
    text = "Email [REDACTED-EMAIL] and phone [REDACTED-PHONE] stay intact."
    result = ENGINE.apply(text)
    assert result["redacted_text"].count("[REDACTED-EMAIL]") == 1
    assert result["redacted_text"].count("[REDACTED-PHONE]") == 1
    assert result["total_redactions"] == 0


def test_partial_email_not_redacted():
    result = ENGINE.apply("Contact john@company without tld")
    assert "[REDACTED-EMAIL]" not in result["redacted_text"]


def test_names_only_when_flagged():
    plain = ENGINE.apply("User Jane Smith wrote this.")
    flagged = ENGINE.apply("redact personal names: User Jane Smith wrote this.")
    assert "[REDACTED-NAME]" not in plain["redacted_text"]
    assert "[REDACTED-NAME]" in flagged["redacted_text"]


def test_contextual_ssn_nine_digits():
    result = ENGINE.apply("SSN 987654321 on file")
    assert "[REDACTED-SSN]" in result["redacted_text"]


def test_deterministic_output():
    first = ENGINE.apply(SAMPLE_INPUT)
    second = ENGINE.apply(SAMPLE_INPUT)
    assert first["redacted_text"] == second["redacted_text"]
    assert first["redactions_applied"] == second["redactions_applied"]


def test_knowledge_mixed_sensitive_example():
    text = (
        "User Jane Smith (jane.smith@email.com, 555-987-6543, SSN 987-65-4321) "
        "used card 5555-5555-5555-4444. redact personal names"
    )
    result = ENGINE.apply(text)
    assert "[REDACTED-NAME]" in result["redacted_text"]
    assert "[REDACTED-EMAIL]" in result["redacted_text"]
    assert "[REDACTED-PHONE]" in result["redacted_text"]
    assert "[REDACTED-SSN]" in result["redacted_text"]
    assert "[REDACTED-CC]" in result["redacted_text"]