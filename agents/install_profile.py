"""Install profile resolution — production (operators) vs ci (pytest only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from agents.env import get_env

PRODUCTION = "production"
CI = "ci"
VALID_PROFILES = frozenset({PRODUCTION, CI})


class ProductionIntegrationError(RuntimeError):
    """Production profile forbids simulated backends or silent integration fallback."""


def get_install_profile(base_path: Optional[Path] = None) -> str:
    """Resolve profile: APXV_PROFILE env overrides managed/config/runtime.json."""
    env_profile = (get_env("APXV_PROFILE") or "").strip().lower()
    if env_profile in VALID_PROFILES:
        return env_profile

    if base_path is not None:
        runtime_path = Path(base_path) / "managed" / "config" / "runtime.json"
        if runtime_path.is_file():
            try:
                data = json.loads(runtime_path.read_text(encoding="utf-8"))
                file_profile = (data.get("profile") or "").strip().lower()
                if file_profile in VALID_PROFILES:
                    return file_profile
            except (json.JSONDecodeError, OSError):
                pass

    return PRODUCTION


def is_production_profile(base_path: Optional[Path] = None) -> bool:
    return get_install_profile(base_path) == PRODUCTION


def write_runtime_profile(base_path: Path, profile: str) -> Dict[str, Any]:
    """Persist install profile to managed/config/runtime.json."""
    if profile not in VALID_PROFILES:
        raise ValueError(f"Invalid install profile: {profile}")

    config_path = base_path / "managed" / "config" / "runtime.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        data = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        data = {
            "version": "2.0.0",
            "deployment": "local-airgapped",
            "store_backend": "sqlite+cas",
            "require_network": False,
        }
    data["profile"] = profile
    config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"path": str(config_path), "profile": profile}


def resolve_llm_backend(llm: Optional[Dict[str, Any]], base_path: Path):
    """Return LLM backend for pipeline/API. Production defaults to Ollama."""
    from agents.llm_backend import OllamaLLMBackend, SimulatedLLMBackend

    config = llm or {}
    backend_name = (config.get("backend") or "").strip().lower()
    profile = get_install_profile(base_path)
    model = config.get("model", "llama3.2")

    if backend_name == "simulated":
        if profile == PRODUCTION:
            raise ProductionIntegrationError(
                "Simulated LLM backend is disabled in production profile. "
                "Install Ollama and run: python -m scripts.apxv_bootstrap"
            )
        return SimulatedLLMBackend()

    if backend_name == "ollama":
        return OllamaLLMBackend(model=model)

    if backend_name:
        if profile == PRODUCTION:
            raise ProductionIntegrationError(
                f"LLM backend '{backend_name}' is not available in production profile. "
                "Use backend=ollama with local Ollama."
            )
        return SimulatedLLMBackend()

    if profile == PRODUCTION:
        return OllamaLLMBackend(model=model)
    return SimulatedLLMBackend()