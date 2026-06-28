"""Smoke tests for the AI Governance Pack."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
PACK = ROOT / "governance-libraries" / "apxv-pack-ai-governance"


def _load_governance_agents():
    mod_path = PACK / "agents" / "governance_agents.py"
    spec = importlib.util.spec_from_file_location("pack_governance_agents_test", mod_path)
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
        "governance/rules/RULE-AI-001.md",
        "governance/workflows/WORKFLOW-AI-001.md",
        "governance/knowledge/KB-AI-001.md",
        "agents/governance_agents.py",
        "capabilities/CAPABILITIES.md",
        "capabilities/policy-delta.json",
        "examples/run_pack_demo.py",
        "examples/inputs/sample.txt",
    ]
    for rel in required:
        assert (pack_root / rel).is_file(), rel


def test_pack_agent_bindings():
    mod = _load_governance_agents()
    assert mod.PACK_AGENT_IDS == (
        "APX-AGENT-001",
        "APX-AGENT-002",
        "APX-AGENT-003",
        "APX-AGENT-LLM-001",
    )
    assert mod.DEFAULT_POLICY_AI == 4


def test_ai_pipeline_sets_compliance_policy_id_4():
    mod = _load_governance_agents()
    from agents.runtime import APXRuntime

    attested = mod.run_governed_ai_pipeline(runtime=APXRuntime())
    output = attested["proposed_artifact"]["output"]
    assert output["compliance_policy_id"] == 4
    assert attested["compliance_policy_id"] == 4
    assert attested["llm_decision"] in ("APPROVED", "REVIEW_REQUIRED", "REJECTED")
    assert output["llm_governance"]["decision"] == attested["llm_decision"]
    assert output["total_redactions"] >= 1
    assert attested["final_status"] == "ATTESTED"


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
    assert "compliance_policy_id=4" in result.stdout
    assert "llm_decision=" in result.stdout
    assert "total_redactions=" in result.stdout


@pytest.mark.skipif(
    not (ROOT / "rust" / "Cargo.toml").exists(),
    reason="Rust workspace not available",
)
def test_ai_attest_includes_compliance_policy_4_proof():
    mod = _load_governance_agents()
    from agents.runtime import APXRuntime
    from agents.zk.bridge import EntityZKBridge
    from agents.zk.compliance_policy import resolve_compliance_policy_id
    from scripts.setup_entity_zk import ensure_entity_zk_setup

    attested = mod.run_governed_ai_pipeline(runtime=APXRuntime())
    assert resolve_compliance_policy_id(attested) == 4

    ensure_entity_zk_setup(base_path=ROOT)
    bundle = EntityZKBridge(base_path=ROOT).generate_entity_proofs(attested)
    assert bundle["metadata"]["compliance_policy_id"] == 4
    assert bundle["proofs"]["compliance"].get("verification_result") is True