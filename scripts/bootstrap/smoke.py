"""Post-bootstrap smoke checks (step 9)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from agents.runtime import APXVRuntime
from scripts.bootstrap.integrations import smoke_check_ollama


def run_smoke(base_path: Path, *, source_root: Path) -> Dict[str, Any]:
    """
    doctor → integrity → reference pack pipeline → attest → verify.

    Uses subprocess for attest/verify so behavior matches operator CLI paths.
    """
    from scripts.apxv_doctor import run_doctor

    report: Dict[str, Any] = {"steps": {}}

    doctor = run_doctor(base_path, check_llm=False)
    report["steps"]["doctor"] = doctor
    doctor_ok = doctor.get("healthy") is True
    if not doctor_ok:
        raise RuntimeError("Smoke failed: apxv_doctor not HEALTHY")

    runtime = APXVRuntime(base_path=base_path)
    integrity = runtime.verify_integrity()
    report["steps"]["integrity"] = integrity
    if not integrity.get("healthy"):
        raise RuntimeError("Smoke failed: runtime integrity not healthy")

    report["steps"]["ollama_integration"] = smoke_check_ollama(base_path)

    pack_demo = (
        source_root
        / "governance-libraries"
        / "apxv-pack-reference-redaction"
        / "examples"
        / "run_pack_demo.py"
    )
    if not pack_demo.is_file():
        raise RuntimeError(f"Smoke failed: reference pack demo missing: {pack_demo}")

    import os

    env = {
        **dict(os.environ),
        "PYTHONPATH": str(source_root),
        "APXV_BASE_PATH": str(base_path),
        "PYTHONWARNINGS": "ignore::RuntimeWarning",
    }
    demo_result = subprocess.run(
        [sys.executable, str(pack_demo)],
        cwd=str(source_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    report["steps"]["reference_pack_demo"] = {
        "returncode": demo_result.returncode,
        "stdout_tail": (demo_result.stdout or "")[-400:],
        "stderr_tail": (demo_result.stderr or "")[-400:],
    }
    if demo_result.returncode != 0:
        raise RuntimeError(
            f"Smoke failed: reference pack demo exit {demo_result.returncode}"
        )

    attest = subprocess.run(
        [sys.executable, "-m", "scripts.run_apxv", "--attest"],
        cwd=str(source_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    report["steps"]["attest"] = {
        "returncode": attest.returncode,
        "stdout_tail": (attest.stdout or "")[-400:],
        "stderr_tail": (attest.stderr or "")[-400:],
    }
    if attest.returncode != 0:
        raise RuntimeError(f"Smoke failed: run_apxv --attest exit {attest.returncode}")

    verify = subprocess.run(
        [sys.executable, "-m", "scripts.verify_attestation", "--real-zk"],
        cwd=str(source_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    report["steps"]["verify"] = {
        "returncode": verify.returncode,
        "stdout_tail": (verify.stdout or "")[-400:],
        "stderr_tail": (verify.stderr or "")[-400:],
    }
    if verify.returncode != 0:
        raise RuntimeError(
            f"Smoke failed: verify_attestation exit {verify.returncode}"
        )

    report["ok"] = True
    return report