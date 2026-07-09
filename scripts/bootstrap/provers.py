"""Build Rust prover binaries when missing (step 2)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict

from scripts.rust_bins import resolve_apxv_circuits_binary, resolve_apxv_zk_binary


def build_provers_if_needed(
    base_path: Path,
    *,
    skip_build: bool = False,
) -> Dict[str, Any]:
    """Compile apxv-circuits and apxv-zk release binaries if not present."""
    circuits_bin = resolve_apxv_circuits_binary(base_path)
    zk_bin = resolve_apxv_zk_binary(base_path)

    report: Dict[str, Any] = {
        "apxv-circuits": str(circuits_bin) if circuits_bin else None,
        "apxv-zk": str(zk_bin) if zk_bin else None,
        "build_ran": False,
        "skipped": False,
    }

    if circuits_bin and zk_bin:
        report["status"] = "present"
        return report

    if skip_build:
        report["skipped"] = True
        report["status"] = "skipped"
        return report

    rust_dir = base_path / "rust"
    manifest = rust_dir / "Cargo.toml"
    if not manifest.is_file():
        raise RuntimeError(f"Rust workspace not found: {manifest}")

    print("[Bootstrap] Building Rust provers (cargo build --release)...")
    result = subprocess.run(
        [
            "cargo",
            "build",
            "--release",
            "--quiet",
            "--manifest-path",
            str(manifest),
            "-p",
            "apxv-circuits",
            "-p",
            "apxv-zk",
        ],
        cwd=str(rust_dir),
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "")[-500:]
        raise RuntimeError(f"cargo build failed: {tail}")

    report["build_ran"] = True
    report["apxv-circuits"] = str(resolve_apxv_circuits_binary(base_path) or "")
    report["apxv-zk"] = str(resolve_apxv_zk_binary(base_path) or "")
    if not report["apxv-circuits"] or not report["apxv-zk"]:
        raise RuntimeError("cargo build completed but prover binaries are still missing")
    report["status"] = "built"
    return report