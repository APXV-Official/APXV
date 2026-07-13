#!/usr/bin/env python3
"""
APX Verification CLI Tool

A trustless, standalone command-line tool for external auditors and third parties
to independently verify APX attestations.

This tool combines:
- Groth16 proof verification (via the Rust binary)
- Artifact chain verification
- Audit log verification

Usage examples:
    apx-verify proof --bundle proof.json --circuit rule-binding
    apx-verify artifacts --dir managed/artifacts
    apx-verify audit --log managed/audit/agent1_audit.log
    apx-verify full --bundle proof.json --artifacts managed/artifacts --audit managed/audit/

All code is original work written for APXV.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Import the helper verification scripts
from verify_audit_log import verify_audit_log
from verify_artifact_chain import verify_artifact_chain


def verify_proof(bundle_path: Path, circuit: str) -> bool:
    """Call the Rust binary to verify a Groth16 proof bundle."""
    rust_binary = Path(__file__).parent.parent / "rust" / "target" / "release" / "apxv-circuits"

    if not rust_binary.exists():
        # Fallback: try to find it in PATH
        rust_binary = "apxv-circuits"

    cmd = [
        str(rust_binary),
        "verify",
        circuit,
        "--proof",
        str(bundle_path)
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        return False

    return "VALID [OK]" in result.stdout


def main():
    parser = argparse.ArgumentParser(
        description="APX Verification CLI — Trustless verification of APX attestations"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Proof verification
    proof_parser = subparsers.add_parser("proof", help="Verify a Groth16 proof bundle")
    proof_parser.add_argument("--bundle", required=True, help="Path to the proof bundle JSON")
    proof_parser.add_argument("--circuit", required=True, choices=["redaction", "rule-binding", "pipeline"],
                              help="Circuit name")

    # Artifact chain verification
    artifacts_parser = subparsers.add_parser("artifacts", help="Verify artifact chain integrity")
    artifacts_parser.add_argument("--dir", required=True, help="Path to the artifacts directory")

    # Audit log verification
    audit_parser = subparsers.add_parser("audit", help="Verify audit log integrity")
    audit_parser.add_argument("--log", required=True, help="Path to the audit log file")

    # Full verification
    full_parser = subparsers.add_parser("full", help="Run multiple verifications together")
    full_parser.add_argument("--bundle", help="Path to the proof bundle JSON")
    full_parser.add_argument("--circuit", choices=["redaction", "rule-binding", "pipeline"],
                             help="Circuit name (required if --bundle is used)")
    full_parser.add_argument("--artifacts", help="Path to the artifacts directory")
    full_parser.add_argument("--audit", help="Path to a specific audit log file")

    args = parser.parse_args()

    success = True

    if args.command == "proof":
        success = verify_proof(Path(args.bundle), args.circuit)

    elif args.command == "artifacts":
        success = verify_artifact_chain(Path(args.dir))

    elif args.command == "audit":
        success = verify_audit_log(Path(args.log))

    elif args.command == "full":
        print("=== APX Full Verification ===\n")

        if args.bundle and args.circuit:
            print("--- Proof Verification ---")
            if not verify_proof(Path(args.bundle), args.circuit):
                success = False

        if args.artifacts:
            print("\n--- Artifact Chain Verification ---")
            if not verify_artifact_chain(Path(args.artifacts)):
                success = False

        if args.audit:
            print("\n--- Audit Log Verification ---")
            if not verify_audit_log(Path(args.audit)):
                success = False

    if success:
        print("\n✅ All requested verifications passed.")
        sys.exit(0)
    else:
        print("\n❌ One or more verifications failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()