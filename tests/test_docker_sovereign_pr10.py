"""PR-10 — Docker image and install scripts must not ship vendor proving keys."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_dockerfile_builds_binaries_only_no_vendor_keys():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert " setup redaction" not in dockerfile
    assert " setup normalization" not in dockerfile
    assert "COPY --from=rust-builder /app/rust/target/release/apxv-circuits" in dockerfile
    assert "COPY --from=rust-builder /app/rust/apxv-circuits/keys" not in dockerfile
    assert "COPY --from=rust-builder /app/rust/apxv-zk/keys" not in dockerfile


def test_dockerignore_excludes_proving_keys():
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "rust/apxv-circuits/keys/" in ignore
    assert "rust/apxv-zk/keys/" in ignore
    assert "managed/config/" in ignore
    assert "\nmanaged/\n" not in f"\n{ignore}\n"


def test_install_docker_ps1_uses_sovereign_bootstrap():
    script = (ROOT / "scripts" / "install-docker.ps1").read_text(encoding="utf-8")
    assert "Seed-ZkKeysFromImage" not in script
    assert "apxv_bootstrap" in script
    assert "--skip-zk" not in script
    assert "--skip-setup" in script


def test_install_docker_sh_uses_sovereign_bootstrap():
    script = (ROOT / "scripts" / "install-docker.sh").read_text(encoding="utf-8")
    assert "seed_zk_keys_from_image" not in script
    assert "apxv_bootstrap" in script
    assert "--skip-zk" not in script
    assert "--skip-setup" in script


def test_docker_entrypoint_calls_apxv_bootstrap():
    entry = (ROOT / "scripts" / "docker_entrypoint.py").read_text(encoding="utf-8")
    assert '"scripts.apxv_bootstrap"' in entry or "'scripts.apxv_bootstrap'" in entry
    # setup_first_run may be imported for key detection; must not be invoked as CLI
    assert '"scripts.setup_first_run"' not in entry
    assert "'scripts.setup_first_run'" not in entry
    assert "--skip-zk" not in entry


def test_vendor_vk_blocklist_has_eleven_hashes():
    from scripts.bootstrap.vendor_blocklist import load_vendor_vk_blocklist, vendor_vk_hashes

    payload = load_vendor_vk_blocklist()
    assert payload.get("description")
    assert len(payload.get("vk_hashes", [])) == 11
    assert len(vendor_vk_hashes()) == 11


def test_needs_sovereign_bootstrap_empty_instance(tmp_path: Path):
    from scripts.docker_entrypoint import needs_sovereign_bootstrap

    assert needs_sovereign_bootstrap(tmp_path) is True


def test_needs_sovereign_bootstrap_after_install_json(tmp_path: Path, monkeypatch):
    from scripts.bootstrap.install_json import build_install_json, write_install_json
    from scripts.docker_entrypoint import needs_sovereign_bootstrap

    def fake_zk(base_path: Path):
        _fake_keys(base_path)
        return {"setup_ran": True}

    monkeypatch.setattr("scripts.bootstrap.orchestrator.run_governance_zk", fake_zk)
    monkeypatch.setattr("scripts.bootstrap.orchestrator.run_entity_zk", fake_zk)

    from scripts.bootstrap.first_run import seed_governance_templates

    seed_governance_templates(tmp_path, ROOT)
    _fake_keys(tmp_path)
    write_install_json(
        tmp_path,
        build_install_json(
            tmp_path,
            profile="ci",
            zk_setup_at="2026-01-01T00:00:00+00:00",
            ollama={"enabled": False, "verified": False, "model": None, "skipped": True},
            voice={"enabled": False, "backend": None, "model": None, "skipped": True},
            sovereign_setup=True,
        ),
    )
    (tmp_path / "managed" / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "managed" / "config" / "capabilities.json").write_text(
        json.dumps({"agents": {}, "signature": "test"}),
        encoding="utf-8",
    )
    assert needs_sovereign_bootstrap(tmp_path) is False


def _fake_keys(base_path: Path) -> None:
    from scripts.bootstrap.constants import ENTITY_CIRCUITS, GOVERNANCE_CIRCUITS

    gov = base_path / "rust" / "apxv-circuits" / "keys"
    ent = base_path / "rust" / "apxv-zk" / "keys"
    gov.mkdir(parents=True, exist_ok=True)
    ent.mkdir(parents=True, exist_ok=True)
    for circuit in GOVERNANCE_CIRCUITS:
        (gov / f"{circuit}.pk").write_bytes(b"pk")
        (gov / f"{circuit}.vk").write_bytes(b"vk")
    for circuit in ENTITY_CIRCUITS:
        (ent / f"{circuit}.pk").write_bytes(b"pk")
        (ent / f"{circuit}.vk").write_bytes(b"vk")