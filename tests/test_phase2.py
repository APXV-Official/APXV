"""Phase 2 governed core hardening tests."""

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.runtime import APXRuntime
from agents.store import SqliteArtifactStore
from agents.audit_logger import AuditLogger
from agents.capability_checker import CapabilityChecker


def test_sqlite_store_write_read_chain():
    store = SqliteArtifactStore(ROOT)
    run_id = uuid.uuid4().hex[:8]
    first = store.write_artifact({"value": 1, "run_id": run_id}, name="test_artifact")
    second = store.write_artifact({"value": 2, "run_id": run_id}, name="test_artifact")
    assert second["previous_artifact"] == first["hash"]

    loaded = store.read_artifact(second["hash"])
    assert loaded["artifact"]["value"] == 2

    chain = store.verify_artifact_chain()
    assert chain["valid"] is True


def test_runtime_initializes_airgapped():
    runtime = APXRuntime()
    status = runtime.get_status()
    assert status["air_gapped"] is True
    assert status["deployment"] == "local-airgapped"
    assert status["store"]["provider"] == "SqliteArtifactStore"


def test_persistent_capabilities_loaded():
    policy_path = ROOT / "managed" / "config" / "capabilities.json"
    logger = AuditLogger(log_path=ROOT / "managed" / "audit" / "test_capability.log")
    checker = CapabilityChecker(
        audit_logger=logger,
        policy_path=policy_path,
        base_path=ROOT,
        require_signed_policy=True,
    )
    assert checker.is_policy_trusted()
    assert checker.has_capability("APXV-AGENT-001", "read_specification")
    assert checker.has_capability("APXV-AGENT-003", "verify_attestation")


def test_governance_registration():
    runtime = APXRuntime()
    spec = runtime.provider.read_specification("rule")
    result = runtime.governance.register_specification(spec)
    assert "content_hash" in result
    active = runtime.governance.get_active_specs()
    assert "rule" in active


def test_runtime_integrity_check():
    runtime = APXRuntime()
    integrity = runtime.verify_integrity()
    assert "store_chain_valid" in integrity
    assert "audit_logs" in integrity