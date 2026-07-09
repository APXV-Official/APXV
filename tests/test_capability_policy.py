"""Tests for signed capability policy (Phase 4 Step 2)."""

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.capability_checker import CapabilityChecker
from agents.capability_policy import (
    CapabilityPolicyError,
    CapabilityPolicyManager,
    policy_content_hash,
)
from agents.audit_logger import AuditLogger


LEGACY_POLICY = {
    "version": "1.0.0",
    "deployment": "local-airgapped",
    "agents": {
        "APXV-AGENT-001": ["read_specification", "write_artifact"],
        "APXV-AGENT-003": ["verify_attestation"],
    },
}


def _write_legacy_policy(tmp_path: Path) -> Path:
    config = tmp_path / "managed" / "config"
    config.mkdir(parents=True)
    policy_path = config / "capabilities.json"
    policy_path.write_text(json.dumps(LEGACY_POLICY, indent=2), encoding="utf-8")
    return policy_path


@pytest.fixture
def policy_env(tmp_path):
    _write_legacy_policy(tmp_path)
    (tmp_path / "managed" / "audit").mkdir(parents=True)
    return tmp_path


def test_migrate_unsigned_policy(policy_env):
    manager = CapabilityPolicyManager(policy_env)
    migrated = manager.migrate_legacy_policy()
    assert migrated is not None
    signed = migrated["signed_policy"]
    assert signed["policy_version"] == 1
    assert signed["signature"]["algorithm"] == "Ed25519"
    manager.verify_document(signed)


def test_capability_checker_rejects_tampered_policy(policy_env):
    manager = CapabilityPolicyManager(policy_env)
    manager.migrate_legacy_policy()

    policy_path = policy_env / "managed" / "config" / "capabilities.json"
    signed = json.loads(policy_path.read_text(encoding="utf-8"))
    signed["agents"]["APXV-AGENT-001"].append("admin")
    policy_path.write_text(json.dumps(signed, indent=2), encoding="utf-8")

    logger = AuditLogger(log_path=policy_env / "managed" / "audit" / "cap.log")
    checker = CapabilityChecker(
        audit_logger=logger,
        base_path=policy_env,
        require_signed_policy=True,
    )
    assert checker.is_policy_trusted() is False
    assert checker.has_capability("APXV-AGENT-001", "read_specification") is False


def test_capability_checker_loads_signed_policy(policy_env):
    manager = CapabilityPolicyManager(policy_env)
    manager.migrate_legacy_policy()

    logger = AuditLogger(log_path=policy_env / "managed" / "audit" / "cap.log")
    checker = CapabilityChecker(
        audit_logger=logger,
        base_path=policy_env,
        require_signed_policy=True,
    )
    assert checker.is_policy_trusted() is True
    assert checker.has_capability("APXV-AGENT-001", "read_specification")
    assert checker.has_capability("APXV-AGENT-003", "verify_attestation")


def test_policy_version_chain(policy_env):
    manager = CapabilityPolicyManager(policy_env)
    manager.migrate_legacy_policy()

    v1 = json.loads(
        (policy_env / "managed" / "config" / "capability_policy_history" / "policy-v1.json").read_text(
            encoding="utf-8"
        )
    )

    v2_agents = copy.deepcopy(LEGACY_POLICY["agents"])
    v2_agents["APXV-AGENT-002"] = ["read_specification"]
    signed_v2 = manager.publish_policy(v2_agents, description="add agent 002")
    assert signed_v2["policy_version"] == 2
    assert signed_v2["previous_policy_hash"] == policy_content_hash(v1)
    manager.verify_document(signed_v2)


def test_grant_and_publish_increments_version(policy_env):
    manager = CapabilityPolicyManager(policy_env)
    manager.migrate_legacy_policy()

    logger = AuditLogger(log_path=policy_env / "managed" / "audit" / "cap.log")
    checker = CapabilityChecker(
        audit_logger=logger,
        base_path=policy_env,
        require_signed_policy=True,
    )
    checker.grant_capability("APXV-AGENT-002", "read_specification", persist=True)
    status = checker.get_status()
    assert status["policy_verified"] is True
    assert status["policy_version"] == 2
    assert checker.has_capability("APXV-AGENT-002", "read_specification")


def test_apx_ctl_policy_verify_roundtrip(policy_env):
    manager = CapabilityPolicyManager(policy_env)
    signed = manager.migrate_legacy_policy()["signed_policy"]
    result = manager.verify_document(signed)
    assert result["valid"] is True