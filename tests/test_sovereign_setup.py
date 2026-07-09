"""PR-11 — install.json provenance, doctor enforcement, integrity sovereign checks."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.runtime import APXVRuntime
from scripts.apxv_doctor import run_doctor
from scripts.bootstrap.constants import ENTITY_CIRCUITS, GOVERNANCE_CIRCUITS
from scripts.bootstrap.install_json import build_install_json, write_install_json
from scripts.bootstrap.sovereign_check import verify_sovereign_setup
from scripts.bootstrap.vendor_blocklist import load_vendor_vk_blocklist


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_show_bytes(relpath: str) -> bytes:
    """Read committed blob — survives CI bootstrap mutating the working tree."""
    result = subprocess.run(
        ["git", "show", f"HEAD:{relpath}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return result.stdout


def _committed_governance_manifest() -> dict:
    return json.loads(
        _git_show_bytes("rust/apxv-circuits/keys/manifest.json").decode("utf-8")
    )


def _copy_vendor_governance_keys(tmp_path: Path) -> None:
    dest = tmp_path / "rust" / "apxv-circuits" / "keys"
    dest.mkdir(parents=True, exist_ok=True)
    for circuit in GOVERNANCE_CIRCUITS:
        for ext in ("pk", "vk"):
            rel = f"rust/apxv-circuits/keys/{circuit}.{ext}"
            try:
                data = _git_show_bytes(rel)
            except subprocess.CalledProcessError:
                continue
            (dest / f"{circuit}.{ext}").write_bytes(data)


def _write_sovereign_keys(tmp_path: Path, *, suffix: bytes = b"operator-vk") -> dict[str, str]:
    gov_dir = tmp_path / "rust" / "apxv-circuits" / "keys"
    ent_dir = tmp_path / "rust" / "apxv-zk" / "keys"
    gov_dir.mkdir(parents=True, exist_ok=True)
    ent_dir.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for circuit in GOVERNANCE_CIRCUITS:
        (gov_dir / f"{circuit}.pk").write_bytes(b"pk")
        vk = gov_dir / f"{circuit}.vk"
        vk.write_bytes(suffix + circuit.encode())
        hashes[circuit] = _sha256_file(vk)
    for circuit in ENTITY_CIRCUITS:
        (ent_dir / f"{circuit}.pk").write_bytes(b"pk")
        vk = ent_dir / f"{circuit}.vk"
        vk.write_bytes(suffix + circuit.encode())
        hashes[circuit] = _sha256_file(vk)
    return hashes


def test_verify_sovereign_pending_without_keys(tmp_path: Path):
    result = verify_sovereign_setup(tmp_path)
    assert result["status"] == "pending"
    assert result["sovereign_ok"] is True
    assert result["sovereign_setup"] is False


def test_doctor_fails_on_vendor_governance_keys(tmp_path: Path):
    _copy_vendor_governance_keys(tmp_path)
    report = run_doctor(tmp_path)
    sovereign = next(c for c in report["checks"] if c["name"] == "sovereign_setup")
    assert sovereign["ok"] is False
    assert report["healthy"] is False
    detail = sovereign["detail"]
    assert detail["vendor_circuits"]


def test_doctor_fails_when_keys_ready_without_install_json(tmp_path: Path):
    hashes = _write_sovereign_keys(tmp_path)
    assert hashes
    integrity = APXVRuntime(base_path=tmp_path).verify_integrity()
    assert integrity["sovereign_ok"] is True
    assert integrity["sovereign_status"] == "pending_provenance"

    report = run_doctor(tmp_path)
    sovereign = next(c for c in report["checks"] if c["name"] == "sovereign_setup")
    assert sovereign["ok"] is False


def test_doctor_passes_after_sovereign_install_json(tmp_path: Path):
    hashes = _write_sovereign_keys(tmp_path)
    write_install_json(
        tmp_path,
        build_install_json(
            tmp_path,
            profile="ci",
            zk_setup_at="2026-07-08T00:00:00+00:00",
            ollama={"enabled": False, "verified": False, "model": None},
            voice={"enabled": False, "backend": None, "model": None},
            sovereign_setup=True,
        ),
    )
    # build_install_json reads on-disk hashes; rewrite with our test hashes
    install_path = tmp_path / "managed" / "config" / "install.json"
    install = json.loads(install_path.read_text(encoding="utf-8"))
    install["vk_hashes"] = hashes
    install_path.write_text(json.dumps(install, indent=2), encoding="utf-8")

    sovereign = verify_sovereign_setup(tmp_path)
    assert sovereign["sovereign_ok"] is True
    assert sovereign["sovereign_setup"] is True
    assert sovereign["status"] == "sovereign"

    report = run_doctor(tmp_path)
    sovereign_check = next(c for c in report["checks"] if c["name"] == "sovereign_setup")
    assert sovereign_check["ok"] is True


def test_doctor_fails_when_install_vk_hashes_mismatch(tmp_path: Path):
    hashes = _write_sovereign_keys(tmp_path)
    write_install_json(
        tmp_path,
        {
            "bootstrap_version": "1.3.0",
            "profile": "ci",
            "sovereign_setup": True,
            "zk_setup_at": "2026-07-08T00:00:00+00:00",
            "host_id": "test",
            "governance_circuits": list(GOVERNANCE_CIRCUITS),
            "entity_circuits": list(ENTITY_CIRCUITS),
            "vk_hashes": {**hashes, "redaction": "0" * 64},
            "ollama": {"enabled": False, "model": None, "verified": False},
            "voice": {"enabled": False, "backend": None, "model": None},
            "bootstrap_completed_at": "2026-07-08T00:00:00+00:00",
        },
    )
    result = verify_sovereign_setup(tmp_path)
    assert result["sovereign_ok"] is False
    assert "vk_hash_mismatch" in " ".join(result["issues"])


def test_vendor_blocklist_matches_manifest_hashes():
    manifest = _committed_governance_manifest()
    blocklist = set(load_vendor_vk_blocklist().get("vk_hashes", []))
    for circuit in GOVERNANCE_CIRCUITS:
        vk_hash = manifest["circuits"][circuit]["vk_hash"]
        assert vk_hash in blocklist


def test_verify_integrity_includes_sovereign_fields(tmp_path: Path):
    _copy_vendor_governance_keys(tmp_path)
    runtime = APXVRuntime(base_path=tmp_path)
    integrity = runtime.verify_integrity()
    assert "sovereign_ok" in integrity
    assert integrity["sovereign_ok"] is False
    assert integrity["healthy"] is False
    assert integrity["sovereign_issues"]