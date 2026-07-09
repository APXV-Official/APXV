"""Bootstrap preflight checks (step 1)."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

from agents.env import get_env

from scripts.rust_bins import resolve_apxv_circuits_binary, resolve_apxv_zk_binary


def run_preflight(base_path: Path, *, source_root: Path) -> Dict[str, Any]:
    """Validate environment before sovereign bootstrap."""
    errors: List[str] = []
    checks: Dict[str, Any] = {}

    major, minor = sys.version_info[:2]
    python_ok = (major, minor) >= (3, 9)
    checks["python"] = {
        "ok": python_ok,
        "detail": f"{major}.{minor}",
        "required": "3.9+",
    }
    if not python_ok:
        errors.append("Python 3.9+ required")

    try:
        base_path.mkdir(parents=True, exist_ok=True)
        probe = base_path / ".bootstrap_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        disk_ok = True
    except OSError as exc:
        disk_ok = False
        errors.append(f"Base path not writable: {exc}")
    checks["disk"] = {"ok": disk_ok, "path": str(base_path)}

    container = get_env("APXV_CONTAINER_BIND") == "1"
    circuits_bin = resolve_apxv_circuits_binary(source_root)
    zk_bin = resolve_apxv_zk_binary(source_root)
    cargo = shutil.which("cargo") is not None
    rustc = shutil.which("rustc") is not None
    provers_ok = (circuits_bin is not None and zk_bin is not None) or (
        container and circuits_bin is not None and zk_bin is not None
    ) or (cargo and rustc)
    checks["provers"] = {
        "ok": provers_ok,
        "apxv-circuits": str(circuits_bin) if circuits_bin else None,
        "apxv-zk": str(zk_bin) if zk_bin else None,
        "cargo": cargo,
        "rustc": rustc,
        "container": container,
    }
    if not provers_ok:
        errors.append(
            "Prover binaries or Rust toolchain required "
            "(native: cargo+rustc or release binaries; Docker: baked binaries)"
        )

    gov_lib = source_root / "governance-libraries"
    checks["governance_libraries"] = {
        "ok": gov_lib.is_dir(),
        "path": str(gov_lib),
    }
    if not gov_lib.is_dir():
        errors.append(f"Missing governance-libraries at {gov_lib}")

    return {
        "ok": len(errors) == 0,
        "checks": checks,
        "errors": errors,
    }