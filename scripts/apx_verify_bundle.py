"""
APX v1 — Standalone Proof Verifier (Phase 1 Criterion #3)

Third-party verification without the full APX Python runtime.
Requires only:
  - This script OR the compiled apx-circuits binary
  - A proof bundle (from an attested artifact or exported JSON)
  - The keys manifest (rust/keys/manifest.json) for VK integrity checks

Usage:
  python -m scripts.apx_verify_bundle <proof_bundle.json> --circuit redaction
  python -m scripts.apx_verify_bundle <attested_artifact.json> --circuit pipeline
"""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts.verify_attestation import verify_real_zk_independent


def _find_apx_circuits_binary() -> Path | None:
    candidates = [
        ROOT / "rust" / "target" / "release" / "apx-circuits.exe",
        ROOT / "rust" / "target" / "release" / "apx-circuits",
        ROOT / "rust" / "target" / "debug" / "apx-circuits.exe",
        ROOT / "rust" / "target" / "debug" / "apx-circuits",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def load_attested_or_bundle(path: Path) -> tuple[dict, dict | None]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "artifact" in data and any(k.startswith("zk_proof_") for k in data["artifact"]):
        return data["artifact"], data
    if "proof_hex" in data and "vk_hex" in data:
        return data, None
    if "artifact" in data:
        return data["artifact"], data
    return data, None


def extract_proof_bundle(attested: dict, circuit: str) -> dict | None:
    key = f"zk_proof_{circuit.replace('-', '_')}"
    bundle = attested.get(key)
    return bundle if isinstance(bundle, dict) else None


def main():
    parser = argparse.ArgumentParser(description="Standalone APX Groth16 proof verifier")
    parser.add_argument("path", type=Path, help="Attested artifact or proof bundle JSON")
    parser.add_argument(
        "--circuit",
        choices=["redaction", "rule-binding", "pipeline", "all"],
        default="all",
        help="Circuit to verify",
    )
    parser.add_argument(
        "--check-binary",
        action="store_true",
        help="Only check that apx-circuits binary is available",
    )
    args = parser.parse_args()

    binary = _find_apx_circuits_binary()
    if args.check_binary:
        if binary:
            print(f"apx-circuits binary found: {binary}")
            return
        print("apx-circuits binary not found. Build with: cargo build --release --manifest-path rust/Cargo.toml")
        sys.exit(1)

    attested, _ = load_attested_or_bundle(args.path)
    circuits = (
        ["redaction", "rule-binding", "pipeline"]
        if args.circuit == "all"
        else [args.circuit]
    )

    all_ok = True
    for circuit in circuits:
        if "proof_hex" in attested and args.circuit != "all":
            # Direct proof bundle file
            result = verify_real_zk_independent(
                {f"zk_proof_{circuit.replace('-', '_')}": attested},
                ROOT,
                circuit=circuit,
            )
        else:
            bundle = extract_proof_bundle(attested, circuit)
            if not bundle:
                print(f"[FAIL] No proof bundle for circuit: {circuit}")
                all_ok = False
                continue
            result = verify_real_zk_independent(attested, ROOT, circuit=circuit)

        ok = result.get("status") == "independent_verification_complete"
        all_ok = all_ok and ok
        print(f"{circuit}: {'VALID' if ok else 'INVALID'} — {result.get('status')}")
        if not ok:
            print(json.dumps(result, indent=2))

    if not all_ok:
        sys.exit(1)
    print("\nStandalone verification complete [OK]")


if __name__ == "__main__":
    main()