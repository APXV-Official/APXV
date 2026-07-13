"""Smoke tests for the Reference Redaction Pack."""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
PACK = ROOT / "governance-libraries" / "apxv-pack-reference-redaction"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_reference_agents():
    mod_path = PACK / "agents" / "reference_agents.py"
    spec = importlib.util.spec_from_file_location("pack_reference_agents_test", mod_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def pack_root() -> Path:
    return PACK


def test_pack_layout_exists(pack_root: Path):
    required = [
        "pack.yaml",
        "README.md",
        "ACCEPTANCE.md",
        "CHANGELOG.md",
        "governance/rules/RULE-RED-001.md",
        "governance/workflows/WORKFLOW-RED-001.md",
        "governance/knowledge/KB-RED-001.md",
        "agents/reference_agents.py",
        "capabilities/CAPABILITIES.md",
        "capabilities/policy-delta.json",
        "examples/run_pack_demo.py",
    ]
    for rel in required:
        assert (pack_root / rel).is_file(), rel


def test_pack_governance_matches_managed_defaults(pack_root: Path):
    pairs = [
        ("governance/rules/RULE-RED-001.md", "managed/rules/rule1.md"),
        ("governance/workflows/WORKFLOW-RED-001.md", "managed/workflows/workflow1.md"),
        ("governance/knowledge/KB-RED-001.md", "managed/knowledge/knowledge1.md"),
    ]
    for pack_rel, managed_rel in pairs:
        assert _sha256(pack_root / pack_rel) == _sha256(ROOT / managed_rel)


def test_pack_agent_bindings():
    mod = _load_reference_agents()
    assert mod.PACK_AGENT_IDS == ("APXV-AGENT-001", "APXV-AGENT-002", "APXV-AGENT-003")
    redactor = mod.RuleGovernedRedactor()
    assert redactor.agent_id == "APXV-AGENT-001"


def test_pack_demo_script_exits_zero():
    result = subprocess.run(
        [sys.executable, str(PACK / "examples" / "run_pack_demo.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-800:]
    assert "final_status=ATTESTED" in result.stdout
    assert "total_redactions=4" in result.stdout