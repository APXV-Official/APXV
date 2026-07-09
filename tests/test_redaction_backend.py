"""Tests for optional BYO redaction backends."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from agents.audit_logger import AuditLogger
from agents.redaction import APXRedactionEngine

ROOT = Path(__file__).parent.parent


def _mock_ml_backend(*, text: str, input_format: str) -> dict:
    redacted = text.replace("secret@corp.com", "[REDACTED-EMAIL]")
    return {
        "redacted_text": redacted,
        "entities": [
            {
                "type": "email",
                "value": "secret@corp.com",
                "start": text.index("secret@corp.com"),
                "category": "EMAIL",
            }
        ],
        "total_redactions": 1,
    }


def test_register_and_invoke_backend():
    engine = APXRedactionEngine()
    backend_id = engine.register_backend("Mock ML Redactor", _mock_ml_backend)
    assert backend_id == "mock-ml-redactor"

    result = engine.apply("Contact secret@corp.com today.", backend_id=backend_id)
    assert result["redacted_text"] == "Contact [REDACTED-EMAIL] today."
    assert result["entity_count"] == 1
    assert result["redaction_backend_id"] == backend_id
    assert result["total_redactions"] == 1


def test_backend_audit_event_logged(tmp_path):
    audit_path = tmp_path / "backend_audit.log"
    logger = AuditLogger(log_path=audit_path)
    engine = APXRedactionEngine(audit_logger=logger)
    backend_id = engine.register_backend("audit-mock", _mock_ml_backend)

    text = "secret@corp.com"
    engine.apply(text, backend_id=backend_id)

    status = logger.get_status()
    assert status["entry_count"] == 1
    assert logger.verify_chain() is True

    import json

    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    event = json.loads(lines[0])
    assert event["event_type"] == "redaction_backend_invoked"
    assert event["data"]["backend_id"] == backend_id
    assert event["data"]["input_hash"] == hashlib.sha256(text.encode()).hexdigest()
    assert event["data"]["entity_count"] == 1


def test_default_apply_without_backend_unchanged():
    engine = APXRedactionEngine()
    result = engine.apply("Email user@example.com")
    assert "[REDACTED-EMAIL]" in result["redacted_text"]
    assert result.get("redaction_backend_id") is None
    assert result["total_redactions"] >= 1


def test_unknown_backend_raises():
    engine = APXRedactionEngine()
    with pytest.raises(KeyError, match="unknown redaction backend"):
        engine.apply("hello", backend_id="missing-backend")


def test_duplicate_backend_registration_raises():
    engine = APXRedactionEngine()
    engine.register_backend("same-name", _mock_ml_backend)
    with pytest.raises(ValueError, match="already registered"):
        engine.register_backend("same-name", _mock_ml_backend)


def _bad_shape_backend(*, text: str, input_format: str) -> dict:
    return {
        "redacted_text": text,
        "entities": [{"unexpected": True}],
    }


def test_dev_warnings_for_malformed_entities(monkeypatch, capsys):
    monkeypatch.setenv("APXV_DEV_WARNINGS", "1")
    engine = APXRedactionEngine()
    backend_id = engine.register_backend("bad-shape", _bad_shape_backend)
    engine.apply("hello", backend_id=backend_id)
    err = capsys.readouterr().err
    assert "APXV_DEV_WARNINGS" in err
    assert backend_id in err


def test_no_dev_warnings_by_default(monkeypatch, capsys):
    monkeypatch.delenv("APXV_DEV_WARNINGS", raising=False)
    engine = APXRedactionEngine()
    backend_id = engine.register_backend("bad-shape-quiet", _bad_shape_backend)
    engine.apply("hello", backend_id=backend_id)
    assert "APXV_DEV_WARNINGS" not in capsys.readouterr().err