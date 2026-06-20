"""
APX v1 — Entity ZK Circuit Setup (Phase 3)

Runs one-time honest trusted setup for all 8 entity Groth16 circuits in apx-zk.
Keys persist under rust/apx-zk/keys/ with a separate entity-manifest.json.
"""

from pathlib import Path
import subprocess
import sys

from .entity_zk_manifest import (
    CIRCUIT_VERSION,
    ENTITY_CIRCUITS,
    rebuild_manifest,
    update_manifest_for_circuit,
)


def ensure_entity_zk_setup(base_path: Path | None = None, force: bool = False) -> dict:
    base = base_path or Path(__file__).parent.parent
    rust_dir = base / "rust"
    crate_dir = rust_dir / "apx-zk"
    manifest = rust_dir / "Cargo.toml"
    keys_dir = crate_dir / "keys"

    report = {"circuits": {}, "setup_ran": False}

    for circuit in ENTITY_CIRCUITS:
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

        print(f"[Entity ZK Setup] Running one-time setup for circuit: {circuit}")
        result = subprocess.run(
            [
                "cargo", "run", "--release",
                "--manifest-path", str(manifest),
                "-p", "apx-zk",
                "--", "setup", circuit,
            ],
            cwd=str(crate_dir),
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            report["circuits"][circuit]["error"] = result.stderr[-500:]
            raise RuntimeError(f"Entity ZK setup failed for {circuit}: {result.stderr[-300:]}")
        report["circuits"][circuit]["setup_complete"] = True
        report["setup_ran"] = True
        manifest_entry = update_manifest_for_circuit(circuit, base_path=base)
        report["circuits"][circuit]["vk_hash"] = manifest_entry["vk_hash"]
        print(result.stdout.strip())
        print(f"      Entity manifest updated: vk_hash={manifest_entry['vk_hash'][:16]}...")

    if not report["setup_ran"]:
        rebuild_manifest(base_path=base)

    return report


def main():
    force = "--force" in sys.argv
    if force:
        print(f"[Entity ZK Setup] Forcing re-setup for circuit version {CIRCUIT_VERSION}")
    report = ensure_entity_zk_setup(force=force)
    print(f"\nEntity ZK setup status (circuit version {CIRCUIT_VERSION}):")
    for circuit, status in report["circuits"].items():
        if status.get("setup_complete"):
            print(f"  {circuit}: setup complete (vk_hash={status.get('vk_hash', '?')[:16]}...)")
        else:
            print(f"  {circuit}: keys already present")


if __name__ == "__main__":
    main()