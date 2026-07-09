"""Resolve pre-built Rust CLI binaries (prefer release over cargo run)."""

from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.env import get_env


def _env_bin(canonical: str) -> Optional[Path]:
    override = get_env(canonical)
    if override:
        path = Path(override)
        if path.exists():
            return path
    return None


def _release_binary_names(stem: str) -> tuple[str, ...]:
    """Prefer platform-native prover binaries (PR-18 cross-platform desktop)."""
    if platform.system() == "Windows":
        return (f"{stem}.exe", stem)
    return (stem, f"{stem}.exe")


def resolve_apxv_circuits_binary(base_path: Optional[Path] = None) -> Optional[Path]:
    base = base_path or ROOT
    found = _env_bin("APXV_CIRCUITS_BIN")
    if found:
        return found
    rust_dir = base / "rust" / "target" / "release"
    for name in _release_binary_names("apxv-circuits"):
        candidate = rust_dir / name
        if candidate.exists():
            return candidate
    which = shutil.which("apxv-circuits")
    if which:
        return Path(which)
    return None


def resolve_apxv_zk_binary(base_path: Optional[Path] = None) -> Optional[Path]:
    base = base_path or ROOT
    found = _env_bin("APXV_ZK_BIN")
    if found:
        return found
    rust_dir = base / "rust" / "target" / "release"
    for name in _release_binary_names("apxv-zk"):
        candidate = rust_dir / name
        if candidate.exists():
            return candidate
    which = shutil.which("apxv-zk")
    if which:
        return Path(which)
    return None


def build_apxv_circuits_command(base_path: Path, *args: str) -> tuple[list[str], str]:
    rust_dir = base_path / "rust"
    crate_dir = rust_dir / "apxv-circuits"
    manifest = rust_dir / "Cargo.toml"
    binary = resolve_apxv_circuits_binary(base_path)
    if binary:
        return [str(binary), *args], str(crate_dir)
    return [
        "cargo", "run", "--release", "--quiet",
        "--manifest-path", str(manifest),
        "-p", "apxv-circuits", "--", *args,
    ], str(crate_dir)


def build_apxv_zk_command(base_path: Path, *args: str) -> tuple[list[str], str]:
    rust_dir = base_path / "rust"
    crate_dir = rust_dir / "apxv-zk"
    manifest = rust_dir / "Cargo.toml"
    binary = resolve_apxv_zk_binary(base_path)
    if binary:
        return [str(binary), *args], str(crate_dir)
    return [
        "cargo", "run", "--release", "--quiet",
        "--manifest-path", str(manifest),
        "-p", "apxv-zk", "--", *args,
    ], str(crate_dir)


# v1.3.x compat aliases — removed in v1.4
resolve_apx_circuits_binary = resolve_apxv_circuits_binary
resolve_apx_zk_binary = resolve_apxv_zk_binary
build_apx_circuits_command = build_apxv_circuits_command
build_apx_zk_command = build_apxv_zk_command