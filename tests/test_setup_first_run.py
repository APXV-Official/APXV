"""Tests for first-run setup script."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts.setup_first_run import run_setup


def test_setup_first_run_fresh_instance(tmp_path):
    (tmp_path / "managed" / "rules").mkdir(parents=True)
    (tmp_path / "managed" / "workflows").mkdir(parents=True)
    (tmp_path / "managed" / "knowledge").mkdir(parents=True)

    for spec, name in (
        ("rules", "rule1.md"),
        ("workflows", "workflow1.md"),
        ("knowledge", "knowledge1.md"),
    ):
        src = ROOT / "managed" / spec / name
        if src.exists():
            (tmp_path / "managed" / spec / name).write_text(
                src.read_text(encoding="utf-8"), encoding="utf-8"
            )

    report = run_setup(tmp_path, setup_zk=False)

    assert report["healthy"] is True
    assert (tmp_path / "managed" / "config" / "capabilities.json").exists()
    assert (tmp_path / "managed" / "config" / "server.json").exists()
    assert (tmp_path / "managed" / "config" / "api_keys.json").exists()
    api_step = report["steps"]["api_key"]
    if api_step.get("api_key"):
        hint = tmp_path / "managed" / "config" / "OPERATOR-KEY-default-operator.txt"
        assert hint.is_file()
        assert api_step.get("hint_file") == str(hint)

    policy = json.loads(
        (tmp_path / "managed" / "config" / "capabilities.json").read_text(encoding="utf-8")
    )
    assert policy.get("signature")
    assert "APX-AGENT-001" in policy.get("agents", {})