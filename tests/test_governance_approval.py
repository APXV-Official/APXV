"""Tests for governance change approval workflow (Phase 4 Step 3)."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.governance_approval import GovernanceApprovalError, GovernanceApprovalWorkflow
from agents.runtime import APXRuntime
from agents.pipeline_service import run_pipeline_quiet


def _seed_managed_tree(target: Path) -> None:
    managed = target / "managed"
    for sub in ("config", "store", "audit", "rules", "workflows", "knowledge", "artifacts", "governance"):
        (managed / sub).mkdir(parents=True, exist_ok=True)

    for rel in ("rules/rule1.md", "workflows/workflow1.md", "knowledge/knowledge1.md"):
        src = ROOT / "managed" / rel
        dst = managed / rel
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    legacy = ROOT / "managed" / "config" / "capabilities.json.legacy"
    if legacy.exists():
        (managed / "config" / "capabilities.json").write_text(
            legacy.read_text(encoding="utf-8"), encoding="utf-8"
        )


@pytest.fixture
def governed_env(tmp_path):
    _seed_managed_tree(tmp_path)
    runtime = APXRuntime(base_path=tmp_path)
    return tmp_path, runtime


def test_bootstrap_active_specs(governed_env):
    _, runtime = governed_env
    status = runtime.governance.approval.get_status()
    assert status["verification"]["valid"] is True
    for spec_type in ("rule", "workflow", "knowledge"):
        assert status["active_approvals"][spec_type] is not None


def test_propose_approve_apply_flow(governed_env):
    base, runtime = governed_env
    original = (base / "managed" / "rules" / "rule1.md").read_text(encoding="utf-8")
    proposed = original + "\n\n## Approval Test Marker\n"

    proposal = runtime.governance.propose_change(
        "rule",
        proposed,
        proposed_by="test-operator",
        summary="test rule update",
    )
    assert proposal["status"] == "proposed"

    approved = runtime.governance.approve_proposal(proposal["id"], approved_by="test-approver")
    assert approved["approval"]["signature"]["algorithm"] == "Ed25519"

    applied = runtime.governance.apply_proposal(proposal["id"])
    assert applied["status"] == "applied"
    assert "Approval Test Marker" in (base / "managed" / "rules" / "rule1.md").read_text(encoding="utf-8")


def test_unapproved_direct_edit_blocks_pipeline(governed_env):
    base, runtime = governed_env
    rule_path = base / "managed" / "rules" / "rule1.md"
    rule_path.write_text(rule_path.read_text(encoding="utf-8") + "\nTAMPERED\n", encoding="utf-8")

    with pytest.raises(GovernanceApprovalError, match="unapproved change"):
        run_pipeline_quiet(input_text="no pii", attest=False, runtime=runtime)


def test_reject_proposal(governed_env):
    _, runtime = governed_env
    original = (runtime.base_path / "managed" / "rules" / "rule1.md").read_text(encoding="utf-8")
    proposal = runtime.governance.propose_change(
        "rule",
        original + "\nRejected change\n",
        summary="should be rejected",
    )
    rejected = runtime.governance.reject_proposal(proposal["id"], reason="not needed")
    assert rejected["status"] == "rejected"

    with pytest.raises(GovernanceApprovalError, match="must be approved"):
        runtime.governance.apply_proposal(proposal["id"])


def test_identical_proposal_rejected(governed_env):
    _, runtime = governed_env
    content = (runtime.base_path / "managed" / "rules" / "rule1.md").read_text(encoding="utf-8")
    with pytest.raises(GovernanceApprovalError, match="identical"):
        runtime.governance.propose_change("rule", content)


def test_workflow_standalone(governed_env):
    base, runtime = governed_env
    workflow = GovernanceApprovalWorkflow(runtime.store, base_path=base, audit_logger=runtime.system_audit)
    verification = workflow.verify_active_specs()
    assert verification["valid"] is True