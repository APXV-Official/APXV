"""Tests for deep_redact_with_count and format-aware apply()."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.redaction import APXRedactionEngine, deep_redact_with_count
from agents.redaction.engine import run_with_timeout

ENGINE = APXRedactionEngine()


def test_deep_redact_plain_string():
    result = deep_redact_with_count("email: test@foo.com", ENGINE)
    assert result["detections"] >= 1
    assert "test@foo.com" not in json.dumps(result["redacted"])


def test_deep_redact_nested_object():
    payload = {
        "user": {"name": "Alice", "contact": {"email": "alice@corp.com"}},
        "notes": "SSN 123-45-6789 found",
    }
    result = deep_redact_with_count(payload, ENGINE)
    serialized = json.dumps(result["redacted"])
    assert "alice@corp.com" not in serialized
    assert "123-45-6789" not in serialized
    assert len(result["entities"]) >= 2


def test_deep_redact_array():
    payload = ["normal text", "SSN: 987-65-4321", "another@email.com"]
    result = deep_redact_with_count(payload, ENGINE)
    serialized = json.dumps(result["redacted"])
    assert "987-65-4321" not in serialized
    assert "another@email.com" not in serialized
    assert len(result["entities"]) >= 2


def test_deep_redact_null_and_missing_values():
    payload = {"a": None, "b": "safe text"}
    result = deep_redact_with_count(payload, ENGINE)
    assert result["redacted"]["a"] is None
    assert result["redacted"]["b"] == "safe text"


def test_deep_redact_number_passthrough():
    result = deep_redact_with_count(42, ENGINE)
    assert result["redacted"] == 42
    assert result["entities"] == []


def test_apply_json_round_trip():
    payload = '{"email":"john.doe@example.com","phone":"(555) 123-4567"}'
    result = ENGINE.apply(payload)
    assert result["input_format"] == "json"
    assert "john.doe@example.com" not in result["redacted_text"]
    assert "[REDACTED-EMAIL]" in result["redacted_text"]


def test_apply_csv_round_trip():
    csv = "name,email,phone\nAlice,alice@example.com,555-1234\nBob,bob@example.com,555-5678\nCarol,carol@example.com,555-9012"
    result = ENGINE.apply(csv)
    assert result["input_format"] == "csv"
    assert "alice@example.com" not in result["redacted_text"]
    assert result["entity_count"] >= 3


def test_run_with_timeout_resolves_fast_call():
    assert run_with_timeout(lambda: "ok", 2, "timed out") == "ok"


def test_run_with_timeout_raises_on_slow_call():
    import time

    def slow():
        time.sleep(0.2)
        return "late"

    with pytest.raises(TimeoutError, match="timed out"):
        run_with_timeout(slow, 0.05, "timed out")