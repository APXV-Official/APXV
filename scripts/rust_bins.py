"""Resolve pre-built Rust CLI binaries (prefer release over cargo run)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent


def resolve_apx_circuits_binary(base_path: Optional[Path] = None) -> Optional[Path]:
    base = base_path or ROOT
    override = os.environ.get("APX_CIRCUITS_BIN")
    if override:
        path = Path(override)
        return path if path.exists() else None
    rust_dir = base / "rust" / "target" / "release"
    for name in ("apx-circuits.exe", "apx-circuits"):
        candidate = rust_dir / name
        if candidate.exists():
            return candidate
    return None


def resolve_apx_zk_binary(base_path: Optional[Path] = None) -> Optional[Path]:
    base = base_path or ROOT
    override = os.environ.get("APX_ZK_BIN")
    if override:
        path = Path(override)
        return path if path.exists() else None
    rust_dir = base / "rust" / "target" / "release"
    for name in ("apx-zk.exe", "apx-zk"):
        candidate = rust_dir / name
        if candidate.exists():
            return candidate
    return None


def build_apx_circuits_command(base_path: Path, *args: str) -> tuple[list[str], str]:
    rust_dir = base_path / "rust"
    crate_dir = rust_dir / "apx-circuits"
    manifest = rust_dir / "Cargo.toml"
    binary = resolve_apx_circuits_binary(base_path)
    if binary:
        return [str(binary), *args], str(crate_dir)
    return [
        "cargo", "run", "--release", "--quiet",
        "--manifest-path", str(manifest),
        "-p", "apx-circuits", "--", *args,
    ], str(crate_dir)


def build_apx_zk_command(base_path: Path, *args: str) -> tuple[list[str], str]:
    rust_dir = base_path / "rust"
    crate_dir = rust_dir / "apx-zk"
    manifest = rust_dir / "Cargo.toml"
    binary = resolve_apx_zk_binary(base_path)
    if binary:
        return [str(binary), *args], str(crate_dir)
    return [
        "cargo", "run", "--release", "--quiet",
        "--manifest-path", str(manifest),
        "-p", "apx-zk", "--", *args,
    ], str(crate_dir)