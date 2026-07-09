"""Tests for Pack Studio install/activate/clone (PR-1b)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.pack_catalog import is_official_pack, parse_pack_manifest
from agents.pack_install import (
    PackInstallError,
    activate_pack,
    clone_pack,
    get_active_pack_summary,
    install_pack,
    read_active_pack,
    snapshot_governance,
)
from agents.pipeline_service import run_pipeline_quiet
from agents.runtime import APXRuntime

from tests.helpers import seed_governance_libraries, seed_test_instance


@pytest.fixture
def pack_env(tmp_path):
    seed_governance_libraries(tmp_path)
    seed_test_instance(tmp_path)
    runtime = APXRuntime(base_path=tmp_path)
    return tmp_path, runtime


def test_official_pack_ids():
    assert is_official_pack("apxv-pack-reference-redaction")
    assert not is_official_pack("apxv-pack-test-ui")


def test_install_pack_lists_catalog_entry(pack_env):
    base, _ = pack_env
    result = install_pack(base, "apxv-pack-reference-redaction")
    assert result["installed"] is True
    assert result["official"] is True


def test_activate_official_reference_pack(pack_env):
    base, runtime = pack_env
    result = activate_pack(runtime, "apxv-pack-reference-redaction")
    assert result["pack_id"] == "apxv-pack-reference-redaction"

    active = read_active_pack(base)
    assert active is not None
    assert active["pack_id"] == "apxv-pack-reference-redaction"
    assert "governance_hashes" in active
    assert active["governance_hashes"]["rule"]

    summary = get_active_pack_summary(base)
    assert summary["active"]["pack_id"] == "apxv-pack-reference-redaction"
    assert summary["pack"]["id"] == "apxv-pack-reference-redaction"


def test_activate_snapshots_previous_pack(pack_env):
    base, runtime = pack_env
    activate_pack(runtime, "apxv-pack-reference-redaction")
    activate_pack(runtime, "apxv-pack-document-processing")

    snap = base / "managed" / "pack-snapshots" / "apxv-pack-reference-redaction"
    assert (snap / "rules" / "rule1.md").exists()
    assert (snap / "active_pack.json").exists()

    active = read_active_pack(base)
    assert active["pack_id"] == "apxv-pack-document-processing"
    assert active["previous_pack_id"] == "apxv-pack-reference-redaction"


def test_activate_custom_pack_requires_confirm(pack_env):
    _, runtime = pack_env
    with pytest.raises(PackInstallError, match="confirm"):
        activate_pack(runtime, "apxv-pack-test-ui")

    result = activate_pack(runtime, "apxv-pack-test-ui", confirm=True)
    assert result["pack_id"] == "apxv-pack-test-ui"


def test_clone_pack_creates_new_directory(pack_env):
    base, _ = pack_env
    result = clone_pack(
        base,
        "apxv-pack-reference-redaction",
        new_pack_id="apxv-pack-clone-test",
        name="Clone Test Pack",
        description="RnD clone test",
    )
    assert result["pack_id"] == "apxv-pack-clone-test"
    pack_dir = base / "governance-libraries" / "apxv-pack-clone-test"
    assert pack_dir.is_dir()
    manifest = (pack_dir / "pack.yaml").read_text(encoding="utf-8")
    assert "apxv-pack-clone-test" in manifest


def test_snapshot_governance_writes_files(pack_env):
    base, runtime = pack_env
    activate_pack(runtime, "apxv-pack-reference-redaction")
    rel = snapshot_governance(base, "apxv-pack-reference-redaction")
    assert "managed/pack-snapshots" in rel.replace("\\", "/")
    snap = base / rel
    assert (snap / "rules" / "rule1.md").exists()
    active = json.loads((snap / "active_pack.json").read_text(encoding="utf-8"))
    assert active["pack_id"] == "apxv-pack-reference-redaction"


def test_parse_pack_manifest_reads_agents(pack_env):
    base, _ = pack_env
    pack_dir = base / "governance-libraries" / "apxv-pack-document-processing"
    manifest = parse_pack_manifest(pack_dir)
    assert len(manifest["agents"]) == 3
    assert manifest["agents"][0]["id"] == "APXV-AGENT-001"
    assert manifest["governance"]["rules"][0].endswith("RULE-DOC-001.md")


def test_activate_document_pack_updates_managed_rules(pack_env):
    base, runtime = pack_env
    activate_pack(runtime, "apxv-pack-document-processing")
    rule_text = (base / "managed" / "rules" / "rule1.md").read_text(encoding="utf-8")
    assert "APXV-RULE-DOC-001" in rule_text
    assert "Batch Document Redaction" in rule_text
    active = read_active_pack(base)
    assert active["governance_summary_hash"]
    assert set(active["governance_hashes"]) == {"rule", "workflow", "knowledge"}


def test_activate_document_then_pipeline_compliance_policy(pack_env):
    base, runtime = pack_env
    activate_pack(runtime, "apxv-pack-document-processing")

    from agents.upload_manager import UploadManager

    uploads = UploadManager(base)
    session = uploads.create_session(label="pack-install-test")
    uploads.add_files(
        session["upload_id"],
        [
            {
                "filename": "invoice.txt",
                "content": b"Contact bill@corp.com SSN 123-45-6789",
            }
        ],
    )

    result = run_pipeline_quiet(
        runtime=runtime,
        pack="document",
        upload_id=session["upload_id"],
    )
    assert result.get("final_status") == "ATTESTED"
    assert result.get("compliance_policy_id") == 2


def test_reactivate_same_pack_is_idempotent(pack_env):
    _, runtime = pack_env
    first = activate_pack(runtime, "apxv-pack-reference-redaction")
    second = activate_pack(runtime, "apxv-pack-reference-redaction")
    assert first["active"]["governance_summary_hash"] == second["active"]["governance_summary_hash"]
    assert all(item["status"] == "unchanged" for item in second["spec_results"])


def test_install_pack_returns_agent_manifest(pack_env):
    base, _ = pack_env
    result = install_pack(base, "apxv-pack-document-processing")
    assert len(result["agents"]) == 3
    assert result["agents"][2]["id"] == "APXV-AGENT-003"


def test_apxv_ctl_pack_list_subprocess(pack_env, tmp_path):
    import os
    import subprocess

    seed_governance_libraries(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "apxv_ctl.py"), "pack", "list"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert len(payload["packs"]) >= 3
    assert any(p["id"] == "apxv-pack-reference-redaction" for p in payload["packs"])