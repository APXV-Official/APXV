"""PR-12 — production vs ci install profile enforcement."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.install_profile import (
    ProductionIntegrationError,
    get_install_profile,
    resolve_llm_backend,
    write_runtime_profile,
    PRODUCTION,
    CI,
)
from agents.llm_backend import OllamaLLMBackend, SimulatedLLMBackend
from agents.pipeline_service import _resolve_llm_backend
from agents.runtime import APXVRuntime
from agents.voice.factory import resolve_voice_providers
from scripts.setup_first_run import run_setup


def _seed_governance(tmp_path: Path) -> None:
    for spec, name in (
        ("rules", "rule1.md"),
        ("workflows", "workflow1.md"),
        ("knowledge", "knowledge1.md"),
    ):
        src = ROOT / "managed" / spec / name
        dest = tmp_path / "managed" / spec / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def test_get_install_profile_env_overrides_runtime_json(tmp_path: Path, monkeypatch):
    write_runtime_profile(tmp_path, PRODUCTION)
    monkeypatch.setenv("APXV_PROFILE", CI)
    assert get_install_profile(tmp_path) == CI


def test_get_install_profile_reads_runtime_json(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("APXV_PROFILE", raising=False)
    write_runtime_profile(tmp_path, CI)
    assert get_install_profile(tmp_path) == CI


def test_setup_first_run_writes_production_profile(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("APXV_PROFILE", raising=False)
    _seed_governance(tmp_path)
    report = run_setup(tmp_path, setup_zk=False)
    assert report["healthy"] is True
    runtime_cfg = json.loads(
        (tmp_path / "managed" / "config" / "runtime.json").read_text(encoding="utf-8")
    )
    assert runtime_cfg["profile"] == PRODUCTION


def test_ci_profile_defaults_to_simulated_llm(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APXV_PROFILE", CI)
    backend = resolve_llm_backend(None, tmp_path)
    assert isinstance(backend, SimulatedLLMBackend)


def test_production_profile_defaults_to_ollama(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("APXV_PROFILE", raising=False)
    write_runtime_profile(tmp_path, PRODUCTION)
    backend = resolve_llm_backend(None, tmp_path)
    assert isinstance(backend, OllamaLLMBackend)


def test_production_rejects_simulated_llm(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("APXV_PROFILE", raising=False)
    write_runtime_profile(tmp_path, PRODUCTION)
    with pytest.raises(ProductionIntegrationError, match="Simulated LLM"):
        resolve_llm_backend({"backend": "simulated"}, tmp_path)


def test_ai_pack_production_uses_ollama_not_simulated(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("APXV_PROFILE", raising=False)
    write_runtime_profile(tmp_path, PRODUCTION)
    runtime = APXVRuntime(base_path=tmp_path)
    backend = _resolve_llm_backend(None, runtime)
    assert isinstance(backend, OllamaLLMBackend)
    with pytest.raises(RuntimeError, match="Ollama"):
        backend.complete("Governance review for release")


def test_production_voice_local_without_vosk_raises(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("APXV_PROFILE", raising=False)
    write_runtime_profile(tmp_path, PRODUCTION)
    with pytest.raises(ProductionIntegrationError, match="Vosk"):
        resolve_voice_providers(tmp_path, mode="local")


def test_ci_voice_local_falls_back_to_simulated(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APXV_PROFILE", CI)
    stt, tts, mode = resolve_voice_providers(tmp_path, mode="local")
    assert mode == "simulated-fallback"
    assert stt.transcribe(b"\x00" * 8).provider == "simulated-stt"
    assert tts.synthesize("hi").provider == "simulated-tts"


def test_production_rejects_simulated_voice_mode(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("APXV_PROFILE", raising=False)
    write_runtime_profile(tmp_path, PRODUCTION)
    with pytest.raises(ProductionIntegrationError, match="Simulated voice"):
        resolve_voice_providers(tmp_path, mode="simulated")