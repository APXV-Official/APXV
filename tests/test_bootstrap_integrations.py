"""PR-13 — Ollama + Vosk bootstrap integration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.bootstrap.install_json import read_install_json, write_install_json
from scripts.bootstrap.install_ollama import ensure_ollama, get_ollama_api_status
from scripts.bootstrap.integrations import (
    repair_integrations,
    run_ollama_integration,
    run_voice_integration,
    smoke_check_ollama,
)


def test_run_ollama_integration_skipped():
    result = run_ollama_integration(skip=True)
    assert result["skipped"] is True
    assert result["verified"] is False


def test_run_ollama_integration_ensure_when_not_skipped(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "scripts.bootstrap.integrations.ensure_ollama",
        lambda **kwargs: {
            "enabled": True,
            "verified": True,
            "model": "llama3.2",
            "detail": "ready",
        },
    )
    result = run_ollama_integration(skip=False)
    assert result["verified"] is True
    assert result["skipped"] is False


def test_get_ollama_api_status_unreachable(monkeypatch):
    def _fail(*_args, **_kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", _fail)
    status = get_ollama_api_status()
    assert status["reachable"] is False
    assert status["detail"]


def test_ensure_ollama_without_binary_skips_install_when_disabled(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr(
        "scripts.bootstrap.install_ollama.run_platform_install_script",
        lambda: {"ok": True},
    )
    result = ensure_ollama(allow_install=False)
    assert result["verified"] is False
    assert "PATH" in result["detail"]


def test_run_voice_integration_skipped():
    result = run_voice_integration(Path("/unused"), skip=True)
    assert result["skipped"] is True


def test_run_voice_integration_present(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "scripts.setup_voice.ensure_vosk_model",
        lambda _base: {"status": "present", "path": str(tmp_path / "model")},
    )
    result = run_voice_integration(tmp_path, skip=False)
    assert result["enabled"] is True
    assert result["backend"] == "vosk"


def test_repair_integrations_updates_install_json(tmp_path: Path, monkeypatch):
    write_install_json(
        tmp_path,
        {
            "bootstrap_version": "1.3.0",
            "profile": "production",
            "sovereign_setup": True,
            "zk_setup_at": "2026-01-01T00:00:00+00:00",
            "host_id": "test",
            "governance_circuits": [],
            "entity_circuits": [],
            "vk_hashes": {},
            "ollama": {"enabled": False, "model": None, "verified": False},
            "voice": {"enabled": False, "backend": None, "model": None},
            "bootstrap_completed_at": "2026-01-01T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        "scripts.bootstrap.integrations.ensure_ollama",
        lambda **kwargs: {
            "enabled": True,
            "verified": True,
            "model": "llama3.2",
            "detail": "ready",
        },
    )
    monkeypatch.setattr(
        "scripts.bootstrap.integrations.run_voice_integration",
        lambda _base, skip=False: {
            "enabled": True,
            "backend": "vosk",
            "model": "vosk-model-small-en-us-0.15",
            "skipped": False,
        },
    )
    result = repair_integrations(tmp_path)
    assert result["install_json_updated"] is True
    install = read_install_json(tmp_path)
    assert install["ollama"]["verified"] is True
    assert install["voice"]["enabled"] is True


def test_smoke_check_ollama_skips_when_not_verified(tmp_path: Path):
    write_install_json(
        tmp_path,
        {
            "bootstrap_version": "1.3.0",
            "profile": "production",
            "sovereign_setup": True,
            "zk_setup_at": "2026-01-01T00:00:00+00:00",
            "host_id": "test",
            "governance_circuits": [],
            "entity_circuits": [],
            "vk_hashes": {},
            "ollama": {"enabled": False, "model": None, "verified": False},
            "voice": {"enabled": False, "backend": None, "model": None},
            "bootstrap_completed_at": "2026-01-01T00:00:00+00:00",
        },
    )
    result = smoke_check_ollama(tmp_path)
    assert result["checked"] is False


def test_smoke_check_ollama_fails_when_verified_but_unreachable(tmp_path: Path, monkeypatch):
    write_install_json(
        tmp_path,
        {
            "bootstrap_version": "1.3.0",
            "profile": "production",
            "sovereign_setup": True,
            "zk_setup_at": "2026-01-01T00:00:00+00:00",
            "host_id": "test",
            "governance_circuits": [],
            "entity_circuits": [],
            "vk_hashes": {},
            "ollama": {"enabled": True, "model": "llama3.2", "verified": True},
            "voice": {"enabled": False, "backend": None, "model": None},
            "bootstrap_completed_at": "2026-01-01T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        "scripts.bootstrap.integrations.get_ollama_api_status",
        lambda **kwargs: {"reachable": False, "model_present": False},
    )
    with pytest.raises(RuntimeError, match="unreachable"):
        smoke_check_ollama(tmp_path)