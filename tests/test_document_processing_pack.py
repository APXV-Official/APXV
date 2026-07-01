"""Smoke tests for the Document Processing Pack."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
PACK = ROOT / "governance-libraries" / "apxv-pack-document-processing"


def _load_document_agents():
    mod_path = PACK / "agents" / "document_agents.py"
    spec = importlib.util.spec_from_file_location("pack_document_agents_test", mod_path)
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
        "governance/rules/RULE-DOC-001.md",
        "governance/workflows/WORKFLOW-DOC-001.md",
        "governance/knowledge/KB-DOC-001.md",
        "agents/document_agents.py",
        "capabilities/CAPABILITIES.md",
        "capabilities/policy-delta.json",
        "examples/run_pack_demo.py",
        "examples/inputs/batch/invoice.txt",
        "examples/inputs/batch/customer.json",
    ]
    for rel in required:
        assert (pack_root / rel).is_file(), rel


@pytest.fixture
def isolated_batch_dir(tmp_path: Path) -> Path:
    """Copy only the two canonical batch fixtures — immune to extra files in examples/."""
    src = PACK / "examples" / "inputs" / "batch"
    batch = tmp_path / "batch"
    batch.mkdir()
    for name in ("invoice.txt", "customer.json"):
        (batch / name).write_text((src / name).read_text(encoding="utf-8"), encoding="utf-8")
    return batch


def test_pack_agent_bindings(isolated_batch_dir: Path):
    mod = _load_document_agents()
    assert mod.PACK_AGENT_IDS == ("APX-AGENT-001", "APX-AGENT-002", "APX-AGENT-003")
    assert mod.DEFAULT_POLICY_BATCH == 2
    files = mod.discover_batch_files(isolated_batch_dir)
    assert len(files) == 2


def test_batch_pipeline_sets_compliance_policy_id_2(isolated_batch_dir: Path):
    mod = _load_document_agents()
    from agents.runtime import APXRuntime

    attested = mod.process_batch_directory(
        isolated_batch_dir,
        runtime=APXRuntime(),
        batch_id="test-batch-001",
    )
    output = attested["proposed_artifact"]["output"]
    assert output["compliance_policy_id"] == 2
    assert output["batch_manifest"]["compliance_policy_id"] == 2
    assert output["batch_manifest"]["file_count"] == 2
    assert len(output["batch_manifest"]["files"]) == 2
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
    assert "file_count=2" in result.stdout
    assert "compliance_policy_id=2" in result.stdout
    assert "total_redactions=" in result.stdout


@pytest.mark.skipif(
    not (ROOT / "rust" / "Cargo.toml").exists(),
    reason="Rust workspace not available",
)
def test_batch_attest_includes_compliance_policy_2_proof(isolated_batch_dir: Path):
    mod = _load_document_agents()
    from agents.runtime import APXRuntime
    from agents.zk.bridge import EntityZKBridge
    from agents.zk.compliance_policy import resolve_compliance_policy_id
    from scripts.setup_entity_zk import ensure_entity_zk_setup

    attested = mod.process_batch_directory(
        isolated_batch_dir,
        runtime=APXRuntime(),
    )
    assert resolve_compliance_policy_id(attested) == 2

    ensure_entity_zk_setup(base_path=ROOT)
    bundle = EntityZKBridge(base_path=ROOT).generate_entity_proofs(attested)
    assert bundle["metadata"]["compliance_policy_id"] == 2
    assert bundle["proofs"]["compliance"].get("verification_result") is True