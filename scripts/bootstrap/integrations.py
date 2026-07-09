"""Optional Ollama + Vosk integration (steps 6–7) and repair path."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from scripts.bootstrap.install_json import read_install_json, write_install_json
from scripts.bootstrap.install_ollama import DEFAULT_OLLAMA_MODEL, ensure_ollama, get_ollama_api_status


def run_ollama_integration(*, skip: bool) -> Dict[str, Any]:
    """Step 6 — install/probe Ollama and pull llama3.2 when not skipped."""
    if skip:
        return {
            "enabled": False,
            "verified": False,
            "model": None,
            "skipped": True,
            "detail": "skipped via --skip-ollama",
        }

    result = ensure_ollama(model=DEFAULT_OLLAMA_MODEL, allow_install=True, allow_pull=True)
    result["skipped"] = False
    return result


def run_voice_integration(base_path: Path, *, skip: bool) -> Dict[str, Any]:
    """Step 7 — optional Vosk voice model (download via setup_voice when not skipped)."""
    if skip:
        return {
            "enabled": False,
            "backend": None,
            "model": None,
            "skipped": True,
            "detail": "skipped via --skip-voice",
        }

    from scripts.setup_voice import ensure_vosk_model

    try:
        result = ensure_vosk_model(base_path)
    except Exception as exc:
        return {
            "enabled": False,
            "backend": "vosk",
            "model": "vosk-model-small-en-us-0.15",
            "skipped": False,
            "detail": f"voice setup failed: {exc}",
        }

    present = result.get("status") == "present" or result.get("path")
    return {
        "enabled": bool(present),
        "backend": "vosk" if present else None,
        "model": "vosk-model-small-en-us-0.15" if present else None,
        "skipped": False,
        "path": result.get("path"),
        "detail": result.get("status", "ok"),
    }


def _update_install_json_integrations(
    base_path: Path,
    ollama: Dict[str, Any],
    voice: Dict[str, Any],
) -> Dict[str, Any] | None:
    install = read_install_json(base_path)
    if not install:
        return None
    install["ollama"] = {
        "enabled": bool(ollama.get("enabled")),
        "model": ollama.get("model"),
        "verified": bool(ollama.get("verified")),
    }
    install["voice"] = {
        "enabled": bool(voice.get("enabled")),
        "backend": voice.get("backend"),
        "model": voice.get("model"),
    }
    write_install_json(base_path, install)
    return install


def repair_integrations(base_path: Path) -> Dict[str, Any]:
    """Re-run Ollama + Vosk setup for Settings repair and post-bootstrap fixes."""
    ollama = ensure_ollama(model=DEFAULT_OLLAMA_MODEL, allow_install=True, allow_pull=True)
    ollama["skipped"] = False
    voice = run_voice_integration(base_path, skip=False)
    install = _update_install_json_integrations(base_path, ollama, voice)
    return {
        "ollama": ollama,
        "voice": voice,
        "install_json_updated": install is not None,
        "ok": bool(ollama.get("verified")) and bool(voice.get("enabled")),
    }


def smoke_check_ollama(base_path: Path) -> Dict[str, Any]:
    """Smoke step — verify Ollama API when install.json marks it verified."""
    install = read_install_json(base_path)
    ollama_cfg = (install or {}).get("ollama") or {}
    status = get_ollama_api_status()

    if not ollama_cfg.get("verified"):
        return {"checked": False, "reason": "ollama not verified in install.json", "api": status}

    if not status.get("reachable"):
        raise RuntimeError(
            "Smoke failed: install.json marks Ollama verified but API is unreachable"
        )
    if not status.get("model_present"):
        raise RuntimeError(
            f"Smoke failed: Ollama reachable but default model {DEFAULT_OLLAMA_MODEL} missing"
        )
    return {"checked": True, "api": status}