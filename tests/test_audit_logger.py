"""Tests for audit logger hardening (v1.2.1 — F-006, F-007)."""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.audit_logger import AuditLogger


def test_get_status_tolerates_corrupt_line(tmp_path: Path):
    log_path = tmp_path / "system_audit.log"
    logger = AuditLogger(log_path)

    logger.log_event("test_event", {"ok": True})
    with log_path.open("a", encoding="utf-8") as f:
        f.write('{"truncated": true\n')

    status = logger.get_status()
    assert status["entry_count"] == 1
    assert status["corrupt_line_count"] == 1
    assert status["degraded"] is True
    assert status["chain_valid"] is False


def test_verify_chain_false_on_corrupt_line(tmp_path: Path):
    log_path = tmp_path / "system_audit.log"
    logger = AuditLogger(log_path)
    logger.log_event("first", {"n": 1})
    log_path.write_text(
        log_path.read_text(encoding="utf-8") + '{"bad json"\n',
        encoding="utf-8",
    )
    assert logger.verify_chain() is False


def test_get_status_chain_break_without_corrupt_lines(tmp_path: Path):
    log_path = tmp_path / "system_audit.log"
    logger = AuditLogger(log_path)
    logger.log_event("first", {"n": 1})
    logger.log_event("second", {"n": 2})

    lines = log_path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    entry["previous_hash"] = "tampered"
    lines[0] = json.dumps(entry, sort_keys=True)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    status = logger.get_status()
    assert status["corrupt_line_count"] == 0
    assert status["chain_valid"] is False
    assert status["issue"] == "chain_break"
    assert status["recovery_hint"] is not None
    assert "chain" in status["recovery_hint"].lower()


def test_get_status_corrupt_lines_issue(tmp_path: Path):
    log_path = tmp_path / "system_audit.log"
    logger = AuditLogger(log_path)
    logger.log_event("ok", {"n": 1})
    with log_path.open("a", encoding="utf-8") as f:
        f.write("{not-json\n")

    status = logger.get_status()
    assert status["issue"] == "corrupt_lines"
    assert status["recovery_hint"] is not None
    assert "managed/audit" in status["recovery_hint"]


def test_repair_chain_fixes_forked_previous_hash(tmp_path: Path):
    log_path = tmp_path / "system_audit.log"
    logger = AuditLogger(log_path)
    logger.log_event("first", {"n": 1})
    logger.log_event("second", {"n": 2})

    lines = log_path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    fork = {
        "timestamp": "2026-01-01T00:00:00Z",
        "event_type": "runtime_initialized",
        "data": {"fork": True},
        "previous_hash": first["current_hash"],
        "current_hash": "deadbeef" * 8,
    }
    # Fork shares parent with line 0 while line 1 is in between.
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(second, sort_keys=True) + "\n")
        f.write(json.dumps(fork, sort_keys=True) + "\n")

    assert logger.verify_chain() is False
    repair = logger.repair_chain()
    assert repair["chain_valid"] is True
    assert logger.verify_chain() is True


def test_concurrent_log_event_preserves_chain(tmp_path: Path):
    log_path = tmp_path / "system_audit.log"
    logger = AuditLogger(log_path)
    errors: list[str] = []

    def worker(i: int) -> None:
        try:
            for j in range(5):
                logger.log_event("concurrent", {"worker": i, "seq": j})
        except Exception as exc:
            errors.append(str(exc))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors
    assert logger.verify_chain() is True

    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 50
    for line in lines:
        json.loads(line)