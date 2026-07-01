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