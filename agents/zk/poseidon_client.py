"""Thin client for apxv-zk Poseidon hash helpers (matches Rust native Poseidon)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional, Union

from scripts.rust_bins import build_apx_zk_command, resolve_apx_zk_binary

Number = Union[int, str]


class PoseidonClient:
    def __init__(self, base_path: Optional[Path] = None) -> None:
        self.base_path = base_path or Path(__file__).parent.parent.parent
        self.rust_dir = self.base_path / "rust"
        self.crate_dir = self.rust_dir / "apxv-zk"
        self.manifest = self.rust_dir / "Cargo.toml"
        self._binary = resolve_apx_zk_binary(self.base_path)

    def _run(self, *args: str) -> str:
        cmd, cwd = build_apx_zk_command(self.base_path, *args)
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"apxv-zk {' '.join(args)} failed: {result.stderr[-500:]}"
            )
        return result.stdout.strip()

    def hash_two(self, left: Number, right: Number) -> int:
        output = self._run("hash-two", str(left), str(right))
        return int(output)

    def hash_fields(self, values: List[Number]) -> int:
        if not values:
            raise ValueError("hash_fields requires at least one value")
        if len(values) == 1:
            return int(str(values[0]))
        if len(values) == 2:
            return self.hash_two(values[0], values[1])
        current = self.hash_two(values[0], values[1])
        for value in values[2:]:
            current = self.hash_two(current, value)
        return current


_default_client: Optional[PoseidonClient] = None


def get_poseidon_client(base_path: Optional[Path] = None) -> PoseidonClient:
    global _default_client
    if base_path is not None:
        return PoseidonClient(base_path=base_path)
    if _default_client is None:
        _default_client = PoseidonClient()
    return _default_client


def hash_two(left: Number, right: Number, *, client: Optional[PoseidonClient] = None) -> int:
    return (client or get_poseidon_client()).hash_two(left, right)


def hash_fields(values: List[Number], *, client: Optional[PoseidonClient] = None) -> int:
    return (client or get_poseidon_client()).hash_fields(values)