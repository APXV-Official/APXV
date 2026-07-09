"""CLI output tests for v1.2.2 audit integrity diagnostics (F-014)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.audit_logger import AuditLogger
from tests.helpers import seed_test_instance

PYTHON = sys.executable


def _run_cli(module: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, "-m", module, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _seed_minimal_instance(tmp_path: Path) -> None:
    seed_test_instance(tmp_path)


def test_apx_ctl_integrity_chain_break_hint(tmp_path: Path):
    _seed_minimal_instance(tmp_path)
    log_path = tmp_path / "managed" / "audit" / "system_audit.log"
    logger = AuditLogger(log_path)
    logger.log_event("first", {"n": 1})
    logger.log_event("second", {"n": 2})
    lines = log_path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    entry["current_hash"] = "broken"
    lines[0] = json.dumps(entry, sort_keys=True)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = _run_cli("scripts.apxv_ctl", "integrity", f"--base-path={tmp_path}")

    assert result.returncode == 1
    assert "FAILED" in result.stdout
    assert "chain_break" in result.stdout
    assert "corrupt_lines=0" in result.stdout
    assert "managed/audit" in result.stdout


def test_apx_ctl_integrity_corrupt_lines_hint(tmp_path: Path):
    _seed_minimal_instance(tmp_path)
    log_path = tmp_path / "managed" / "audit" / "system_audit.log"
    logger = AuditLogger(log_path)
    logger.log_event("ok", {"n": 1})
    with log_path.open("a", encoding="utf-8") as f:
        f.write("{bad-json\n")

    result = _run_cli("scripts.apxv_ctl", "integrity", f"--base-path={tmp_path}")

    assert result.returncode == 1
    assert "corrupt_lines" in result.stdout
    assert "managed/audit" in result.stdout


def test_apx_doctor_corrupt_lines_hint(tmp_path: Path):
    _seed_minimal_instance(tmp_path)
    log_path = tmp_path / "managed" / "audit" / "system_audit.log"
    logger = AuditLogger(log_path)
    logger.log_event("ok", {"n": 1})
    with log_path.open("a", encoding="utf-8") as f:
        f.write("{bad-json\n")

    result = _run_cli("scripts.apxv_doctor", f"--base-path={tmp_path}")

    assert result.returncode == 1
    assert "NEEDS ATTENTION" in result.stdout
    assert "corrupt_lines" in result.stdout
    assert "managed/audit" in result.stdout


def test_apx_doctor_chain_break_hint(tmp_path: Path):
    _seed_minimal_instance(tmp_path)
    log_path = tmp_path / "managed" / "audit" / "system_audit.log"
    logger = AuditLogger(log_path)
    logger.log_event("first", {"n": 1})
    logger.log_event("second", {"n": 2})
    lines = log_path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    entry["previous_hash"] = "tampered"
    lines[0] = json.dumps(entry, sort_keys=True)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = _run_cli("scripts.apxv_doctor", f"--base-path={tmp_path}")

    assert result.returncode == 1
    assert "NEEDS ATTENTION" in result.stdout
    assert "chain_break" in result.stdout
    assert "fresh_reset" in result.stdout or "setup_first_run" in result.stdout