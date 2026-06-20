"""Port of legacy redaction-engine pattern matrix tests."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.redaction import APXRedactionEngine

ENGINE = APXRedactionEngine()


@pytest.mark.parametrize(
    "input_text,forbidden",
    [
        ("SSN: 123-45-6789", "123-45-6789"),
        ("Contact: john.doe@example.com for details.", "john.doe@example.com"),
        ("Call us at (555) 867-5309.", "867-5309"),
        ("Card: 4111111111111111", "4111111111111111"),
        ("Social security number: 123 45 6789", "123 45 6789"),
        ("Reach me at user@domain.com anytime.", "user@domain.com"),
        ("Call +1-800-555-1234 for support.", "800-555-1234"),
        ("Phone: 321.222.4455", "321.222.4455"),
        ("Phone: 321 222 4455", "321 222 4455"),
        ("Contact: (321) 222-4455", "222-4455"),
        ("Phone number is (321) 222 4455.", "222 4455"),
        ("Card on file: 4111 1111 1111 1111", "4111 1111 1111 1111"),
        ("DOB: 01/15/1985", "01/15/1985"),
        ("Request from IP 192.168.1.1 was logged.", "192.168.1.1"),
    ],
)
def test_redacts_sensitive_fragment(input_text, forbidden):
    result = ENGINE.redact_pii(input_text)
    assert forbidden not in result["redacted_text"]
    assert result["summary"]["total_detected"] >= 1


def test_plain_text_unchanged():
    text = "The weather today is sunny and warm."
    result = ENGINE.redact_pii(text)
    assert result["entities"] == []
    assert result["redacted_text"] == text


def test_multiple_entity_types_detected():
    input_text = "Patient John Smith, SSN 123-45-6789, Email: john@example.com"
    result = ENGINE.redact_pii(input_text)
    assert result["summary"]["total_detected"] >= 2


def test_summary_shape():
    result = ENGINE.redact_pii("SSN: 123-45-6789")
    assert "by_category" in result["summary"]
    assert "by_severity" in result["summary"]
    assert isinstance(result["summary"]["total_detected"], int)


def test_rejects_oversized_input():
    with pytest.raises(ValueError, match="too large"):
        ENGINE.redact_pii("x" * 600_000)


def test_ssn_entity_type_present():
    result = ENGINE.redact_pii("SSN: 123-45-6789")
    assert any("ssn" in entity["type"].lower() for entity in result["entities"])


def test_credit_card_critical_severity():
    result = ENGINE.redact_pii("Card: 4111111111111111")
    assert any(entity["severity"] == "critical" for entity in result["entities"])


def test_phase0_combined_string():
    input_text = ", ".join(
        [
            "Name: John Smith",
            "DOB: 01/15/1985",
            "SSN: 123-45-6789",
            "Phone: (321) 222-4455",
            "Email: user@domain.com",
            "Card: 4111 1111 1111 1111",
            "IP: 192.168.1.1",
        ]
    )
    result = ENGINE.redact_pii(input_text)
    for forbidden in (
        "John Smith",
        "01/15/1985",
        "123-45-6789",
        "222-4455",
        "user@domain.com",
        "4111 1111 1111 1111",
        "192.168.1.1",
    ):
        assert forbidden not in result["redacted_text"]
    assert result["summary"]["total_detected"] >= 6


def test_name_redacted_when_flagged_in_apply():
    flagged = ENGINE.apply("redact personal names: User Jane Smith wrote this.")
    assert "[REDACTED-NAME]" in flagged["redacted_text"]


def test_compiled_pattern_count():
    from agents.redaction.patterns import ALL_PATTERN_DEFINITIONS, compile_patterns

    assert len(ALL_PATTERN_DEFINITIONS) >= 75
    assert len(compile_patterns()) >= 60