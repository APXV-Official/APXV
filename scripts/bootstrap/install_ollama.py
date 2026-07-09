"""Ollama install + model pull helpers (PR-13 bootstrap step 6)."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_OLLAMA_MODEL = "llama3.2"
OLLAMA_API_BASE = "http://127.0.0.1:11434"


def get_ollama_api_status(*, timeout: float = 3.0) -> Dict[str, Any]:
    """Probe local Ollama tags API (same contract as GET /api/v2/integrations/ollama)."""
    result: Dict[str, Any] = {
        "reachable": False,
        "models": [],
        "detail": None,
        "model_present": False,
        "default_model": DEFAULT_OLLAMA_MODEL,
    }
    try:
        with urllib.request.urlopen(f"{OLLAMA_API_BASE}/api/tags", timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            models: List[Dict[str, Any]] = [
                {"name": item.get("name"), "size": item.get("size")}
                for item in payload.get("models", [])
            ]
            result["reachable"] = resp.status == 200
            result["models"] = models
            names = {str(m.get("name", "")).split(":")[0] for m in models}
            result["model_present"] = DEFAULT_OLLAMA_MODEL in names
    except Exception as exc:
        result["detail"] = str(exc)
    return result


def _run_command(cmd: List[str], *, timeout: int = 600) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "returncode": completed.returncode,
            "stdout": (completed.stdout or "")[-800:],
            "stderr": (completed.stderr or "")[-800:],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"returncode": -1, "stdout": "", "stderr": str(exc)}


def pull_ollama_model(model: str = DEFAULT_OLLAMA_MODEL) -> Dict[str, Any]:
    if not shutil.which("ollama"):
        return {"ok": False, "detail": "ollama not on PATH"}
    result = _run_command(["ollama", "pull", model], timeout=1800)
    result["ok"] = result["returncode"] == 0
    result["model"] = model
    return result


def run_platform_install_script() -> Dict[str, Any]:
    """Invoke bootstrap/install_ollama.ps1 or .sh (winget / curl installer)."""
    script_dir = Path(__file__).resolve().parent
    if sys.platform == "win32":
        script = script_dir / "install_ollama.ps1"
        if not script.is_file():
            return {"ok": False, "detail": f"missing installer: {script}"}
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ]
    else:
        script = script_dir / "install_ollama.sh"
        if not script.is_file():
            return {"ok": False, "detail": f"missing installer: {script}"}
        cmd = ["bash", str(script)]

    result = _run_command(cmd, timeout=1800)
    result["ok"] = result["returncode"] == 0
    result["platform"] = platform.system()
    result["script"] = str(script)
    return result


def ensure_ollama(
    *,
    model: str = DEFAULT_OLLAMA_MODEL,
    allow_install: bool = True,
    allow_pull: bool = True,
) -> Dict[str, Any]:
    """Install Ollama when missing, probe API, pull default model when needed."""
    from agents.env import get_env

    report: Dict[str, Any] = {
        "enabled": False,
        "verified": False,
        "model": model,
        "skipped": False,
        "install_ran": False,
        "pull_ran": False,
    }

    if get_env("APXV_CONTAINER_BIND") == "1":
        status = get_ollama_api_status()
        report.update(
            {
                "enabled": status["reachable"],
                "verified": status["reachable"] and status.get("model_present", False),
                "detail": (
                    "container bind — use host Ollama on :11434 or a compose sidecar "
                    "(see docs/DOCKER.md)"
                    if not status["reachable"]
                    else "reachable from container"
                ),
                "api": status,
            }
        )
        return report

    if not shutil.which("ollama"):
        if not allow_install:
            report["detail"] = "ollama not on PATH — install skipped"
            return report
        install = run_platform_install_script()
        report["install_ran"] = True
        report["install"] = install
        if not install.get("ok"):
            report["detail"] = "ollama install failed — AI Governance pack unavailable"
            return report
        for _ in range(30):
            if get_ollama_api_status(timeout=2.0)["reachable"]:
                break
            time.sleep(2)

    status = get_ollama_api_status()
    report["api"] = status
    if not status["reachable"]:
        report["detail"] = (
            "ollama present but API unreachable — start Ollama or use --skip-ollama"
        )
        return report

    if allow_pull and not status.get("model_present"):
        pull = pull_ollama_model(model)
        report["pull_ran"] = True
        report["pull"] = pull
        status = get_ollama_api_status()
        report["api"] = status

    report["enabled"] = True
    report["verified"] = bool(status.get("model_present"))
    if report["verified"]:
        report["detail"] = f"ollama ready with model {model}"
    else:
        report["detail"] = f"ollama reachable but model {model} not present after pull"
    return report