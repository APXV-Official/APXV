"""Tests for sovereign bootstrap orchestrator (PR-9)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.apxv_bootstrap import main as bootstrap_main
from scripts.bootstrap.constants import ENTITY_CIRCUITS, GOVERNANCE_CIRCUITS
from scripts.bootstrap.install_json import read_install_json
from scripts.bootstrap.orchestrator import BootstrapOptions, run_bootstrap
from scripts.bootstrap.preflight import run_preflight


def _seed_governance_only(tmp_path: Path) -> None:
    for spec_dir, filename in (
        ("rules", "rule1.md"),
        ("workflows", "workflow1.md"),
        ("knowledge", "knowledge1.md"),
    ):
        src = ROOT / "managed" / spec_dir / filename
        if not src.is_file():
            continue
        dest = tmp_path / "managed" / spec_dir / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _fake_zk_keys(base_path: Path) -> None:
    gov_dir = base_path / "rust" / "apxv-circuits" / "keys"
    entity_dir = base_path / "rust" / "apxv-zk" / "keys"
    gov_dir.mkdir(parents=True, exist_ok=True)
    entity_dir.mkdir(parents=True, exist_ok=True)
    for circuit in GOVERNANCE_CIRCUITS:
        (gov_dir / f"{circuit}.pk").write_bytes(b"test-pk")
        (gov_dir / f"{circuit}.vk").write_bytes(b"test-vk")
    for circuit in ENTITY_CIRCUITS:
        (entity_dir / f"{circuit}.pk").write_bytes(b"test-pk")
        (entity_dir / f"{circuit}.vk").write_bytes(b"test-vk")


def test_preflight_requires_writable_base(tmp_path: Path):
    result = run_preflight(tmp_path, source_root=ROOT)
    assert result["ok"] is True
    assert result["checks"]["python"]["ok"] is True


def test_bootstrap_fresh_tmp_path_writes_install_json(tmp_path: Path, monkeypatch):
    _seed_governance_only(tmp_path)

    def fake_gov(base_path: Path):
        _fake_zk_keys(base_path)
        return {"setup_ran": True, "keys_ready": True}

    def fake_entity(base_path: Path):
        return {"setup_ran": True, "keys_ready": True}

    monkeypatch.setattr("scripts.bootstrap.orchestrator.run_governance_zk", fake_gov)
    monkeypatch.setattr("scripts.bootstrap.orchestrator.run_entity_zk", fake_entity)

    options = BootstrapOptions(
        base_path=tmp_path,
        source_root=ROOT,
        skip_ollama=True,
        skip_voice=True,
        skip_smoke=True,
        skip_prover_build=True,
        profile="ci",
    )
    report = run_bootstrap(options)

    assert report.ok is True
    assert report.sovereign_setup is True
    assert report.exit_code == 0

    install = read_install_json(tmp_path)
    assert install is not None
    assert install["sovereign_setup"] is True
    assert install["bootstrap_version"] == "1.3.0"
    assert install["profile"] == "ci"
    assert len(install["vk_hashes"]) == len(GOVERNANCE_CIRCUITS) + len(ENTITY_CIRCUITS)
    assert (tmp_path / "managed" / "config" / "capabilities.json").is_file()
    assert (tmp_path / "managed" / "config" / "runtime.json").is_file()
    runtime_cfg = json.loads(
        (tmp_path / "managed" / "config" / "runtime.json").read_text(encoding="utf-8")
    )
    assert runtime_cfg["profile"] == "ci"


def test_bootstrap_cli_json_report(tmp_path: Path, monkeypatch):
    _seed_governance_only(tmp_path)

    def fake_gov(base_path: Path):
        _fake_zk_keys(base_path)
        return {"setup_ran": True}

    monkeypatch.setattr("scripts.bootstrap.orchestrator.run_governance_zk", fake_gov)
    monkeypatch.setattr("scripts.bootstrap.orchestrator.run_entity_zk", fake_gov)

    code = bootstrap_main(
        [
            "--base-path",
            str(tmp_path),
            "--source-root",
            str(ROOT),
            "--skip-ollama",
            "--skip-voice",
            "--skip-smoke",
            "--skip-prover-build",
            "--profile",
            "ci",
            "--json-report",
        ]
    )
    assert code == 0
    install = read_install_json(tmp_path)
    assert install["sovereign_setup"] is True


def test_bootstrap_exit_partial_when_ollama_missing(tmp_path: Path, monkeypatch):
    _seed_governance_only(tmp_path)

    def fake_gov(base_path: Path):
        _fake_zk_keys(base_path)
        return {"setup_ran": True}

    monkeypatch.setattr("scripts.bootstrap.orchestrator.run_governance_zk", fake_gov)
    monkeypatch.setattr("scripts.bootstrap.orchestrator.run_entity_zk", fake_gov)
    monkeypatch.setattr(
        "scripts.bootstrap.integrations.ensure_ollama",
        lambda **kwargs: {
            "enabled": False,
            "verified": False,
            "model": "llama3.2",
            "skipped": False,
            "detail": "ollama not on PATH — AI Governance pack unavailable",
        },
    )

    options = BootstrapOptions(
        base_path=tmp_path,
        source_root=ROOT,
        skip_ollama=False,
        skip_voice=True,
        skip_smoke=True,
        skip_prover_build=True,
        profile="ci",
    )
    report = run_bootstrap(options)
    assert report.ok is True
    assert report.exit_code == 2
    assert report.partial is True


def test_bootstrap_fails_preflight_on_missing_governance_libs(tmp_path: Path, monkeypatch):
    bogus_root = tmp_path / "empty-root"
    bogus_root.mkdir()
    options = BootstrapOptions(
        base_path=tmp_path / "instance",
        source_root=bogus_root,
        skip_ollama=True,
        skip_voice=True,
        skip_smoke=True,
        skip_prover_build=True,
        profile="ci",
    )
    report = run_bootstrap(options)
    assert report.ok is False
    assert report.exit_code == 1
    assert report.sovereign_setup is False
    assert read_install_json(tmp_path / "instance") is None


def test_bootstrap_integration_with_real_zk(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("APXV_BASE_PATH", raising=False)
    monkeypatch.delenv("APXV_PROFILE", raising=False)
    """Gate-style run on isolated tmp_path when Rust provers are available."""
    from scripts.rust_bins import resolve_apxv_circuits_binary, resolve_apxv_zk_binary

    if not resolve_apxv_circuits_binary(ROOT) or not resolve_apxv_zk_binary(ROOT):
        pytest.skip("Release prover binaries not built")

    _seed_governance_only(tmp_path)
    options = BootstrapOptions(
        base_path=tmp_path,
        source_root=ROOT,
        skip_ollama=True,
        skip_voice=True,
        skip_smoke=True,
        skip_prover_build=True,
        profile="ci",
    )
    report = run_bootstrap(options)
    assert report.ok is True
    install = read_install_json(tmp_path)
    assert install["sovereign_setup"] is True