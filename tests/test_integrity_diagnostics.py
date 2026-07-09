"""Tests for v1.2.2 audit integrity diagnostics (F-014)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.audit_logger import AuditLogger
from agents.runtime import APXRuntime


def test_verify_integrity_includes_audit_summary(tmp_path: Path, monkeypatch):
    audit_dir = tmp_path / "managed" / "audit"
    audit_dir.mkdir(parents=True)
    log_path = audit_dir / "system_audit.log"
    logger = AuditLogger(log_path)
    logger.log_event("event", {"ok": True})
    with log_path.open("a", encoding="utf-8") as f:
        f.write('{"truncated": true\n')

    runtime = APXRuntime(base_path=tmp_path)
    integrity = runtime.verify_integrity()

    assert integrity["healthy"] is False
    assert "audit_summary" in integrity
    assert "sovereign_ok" in integrity
    assert integrity["sovereign_ok"] is True
    assert "system_audit.log" in integrity["audit_summary"]
    summary = integrity["audit_summary"]["system_audit.log"]
    assert summary["issue"] == "corrupt_lines"
    assert summary["corrupt_line_count"] == 1
    assert integrity["recovery_hints"]


def test_health_payload_includes_audit_summary(api_server):
    base, _, tmp_path = api_server
    audit_dir = tmp_path / "managed" / "audit"
    log_path = audit_dir / "system_audit.log"
    logger = AuditLogger(log_path)
    logger.log_event("first", {"n": 1})
    logger.log_event("second", {"n": 2})
    lines = log_path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    entry["current_hash"] = "broken"
    lines[0] = json.dumps(entry, sort_keys=True)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    import urllib.request

    with urllib.request.urlopen(f"{base}/health", timeout=10) as resp:
        data = json.loads(resp.read().decode())

    assert data["status"] == "degraded"
    assert "sovereign_setup" in data
    summary = data["integrity"]["audit_summary"]["system_audit.log"]
    assert summary["issue"] == "chain_break"
    assert summary["corrupt_line_count"] == 0