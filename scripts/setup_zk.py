"""
APXV — ZK Circuit Setup

Runs the one-time honest trusted setup for all three Groth16 circuits.
Keys are persisted under rust/apxv-circuits/keys/ and reused for every subsequent proof.
"""

from pathlib import Path
import subprocess
import sys

from .rust_bins import build_apx_circuits_command
from .zk_manifest import (
    CIRCUIT_VERSION,
    rebuild_manifest,
    update_manifest_for_circuit,
)


CIRCUITS = ("redaction", "rule-binding", "pipeline")


def ensure_zk_setup(base_path: Path | None = None, force: bool = False) -> dict:
    """Ensure trusted setup keys exist for all circuits. Returns a status report."""
    base = base_path or Path(__file__).parent.parent
    rust_dir = base / "rust"
    crate_dir = rust_dir / "apxv-circuits"
    manifest = rust_dir / "Cargo.toml"
    keys_dir = crate_dir / "keys"

    report = {"circuits": {}, "setup_ran": False}

    for circuit in CIRCUITS:
        pk = keys_dir / f"{circuit}.pk"
        vk = keys_dir / f"{circuit}.vk"
        needs_setup = force or not pk.exists() or not vk.exists()
        report["circuits"][circuit] = {
            "pk_exists": pk.exists(),
            "vk_exists": vk.exists(),
            "needs_setup": needs_setup,
        }

        if not needs_setup:
            continue

        print(f"[ZK Setup] Running one-time setup for circuit: {circuit}")
        cmd, cwd = build_apx_circuits_command(base, "setup", circuit)
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            report["circuits"][circuit]["error"] = result.stderr[-500:]
            raise RuntimeError(f"ZK setup failed for {circuit}: {result.stderr[-300:]}")
        report["circuits"][circuit]["setup_complete"] = True
        report["setup_ran"] = True
        manifest_entry = update_manifest_for_circuit(circuit, base_path=base)
        report["circuits"][circuit]["vk_hash"] = manifest_entry["vk_hash"]
        print(result.stdout.strip())
        print(f"      Manifest updated: vk_hash={manifest_entry['vk_hash'][:16]}...")

    if not report["setup_ran"]:
        rebuild_manifest(base_path=base)

    return report


def main():
    force = "--force" in sys.argv
    if force:
        print(f"[ZK Setup] Forcing re-setup for circuit version {CIRCUIT_VERSION}")
    report = ensure_zk_setup(force=force)
    print(f"\nZK setup status (circuit version {CIRCUIT_VERSION}):")
    for circuit, status in report["circuits"].items():
        if status.get("setup_complete"):
            print(f"  {circuit}: setup complete (vk_hash={status.get('vk_hash', '?')[:16]}...)")
        else:
            vk = status.get("vk_hash") or "unchanged"
            print(f"  {circuit}: keys already present ({vk})")


if __name__ == "__main__":
    main()