"""Tests for APX entity ZK crate (Phase 3)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts.entity_zk_manifest import ENTITY_CIRCUITS, manifest_path


@pytest.mark.parametrize("circuit", ENTITY_CIRCUITS)
def test_entity_circuit_is_listed(circuit: str):
    assert circuit in ENTITY_CIRCUITS


def test_entity_manifest_template_exists():
    path = manifest_path(ROOT)
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["manifest_version"] == "1.0.0"
    assert "circuits" in data


@pytest.mark.skipif(
    not (ROOT / "rust" / "Cargo.toml").exists(),
    reason="Rust workspace not available",
)
def test_apx_zk_cargo_tests_pass():
    result = subprocess.run(
        [
            "cargo", "test", "--manifest-path", str(ROOT / "rust" / "Cargo.toml"),
            "-p", "apx-zk", "-q",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "57 passed" in result.stdout or "test result: ok" in result.stdout