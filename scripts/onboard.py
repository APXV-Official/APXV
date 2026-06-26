"""
APXV1 onboarding — setup, pack demo, attest, and independent verify.

    python -m scripts.onboard

Used by install.ps1 / install.sh. In Docker (ZK keys baked in image):

    python -m scripts.onboard --skip-zk
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PACK_DEMO = (
    ROOT
    / "governance-libraries"
    / "apxv-pack-reference-redaction"
    / "examples"
    / "run_pack_demo.py"
)


def _run(label: str, args: list[str], *, step: int, total: int) -> None:
    print()
    print("=" * 60)
    print(f"[{step}/{total}] {label}")
    print("=" * 60)
    env = {**dict(__import__("os").environ), "PYTHONWARNINGS": "ignore::RuntimeWarning"}
    result = subprocess.run(args, cwd=ROOT, env=env)
    if result.returncode != 0:
        print(f"\nFAILED: {label} (exit {result.returncode})", file=sys.stderr)
        raise SystemExit(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="APXV1 onboarding — setup, pack demo, attest, verify"
    )
    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="Skip setup_first_run (instance already initialized)",
    )
    parser.add_argument(
        "--skip-zk",
        action="store_true",
        help="Pass --skip-zk to setup_first_run (Docker image with baked keys)",
    )
    args = parser.parse_args()

    if not PACK_DEMO.is_file():
        print(f"ERROR: pack demo not found: {PACK_DEMO}", file=sys.stderr)
        return 1

    py = sys.executable
    total = 5 if args.skip_setup else 6
    step = 1

    print("=" * 60)
    print("APXV1 onboarding (v1.1.2)")
    print("Platform setup → Reference Redaction Pack → attest → verify")
    print("=" * 60)

    if not args.skip_setup:
        setup_args = [py, "-m", "scripts.setup_first_run"]
        if args.skip_zk:
            setup_args.append("--skip-zk")
        _run("First-run setup", setup_args, step=step, total=total)
        step += 1

    _run("Doctor check", [py, "-m", "scripts.apx_doctor"], step=step, total=total)
    step += 1

    _run("Integrity check", [py, "-m", "scripts.apx_ctl", "integrity"], step=step, total=total)
    step += 1

    _run("Reference Redaction Pack demo", [py, str(PACK_DEMO)], step=step, total=total)
    step += 1

    _run(
        "Platform pipeline + attestation",
        [py, "-m", "scripts.run_apx", "--attest"],
        step=step,
        total=total,
    )
    step += 1

    _run(
        "Independent ZK verification",
        [py, "-m", "scripts.verify_attestation", "--real-zk"],
        step=step,
        total=total,
    )

    print()
    print("=" * 60)
    print("Onboarding complete.")
    print("  Pack demo:  final_status=ATTESTED, total_redactions=4")
    print("  Next:       python -m scripts.apx_serve")
    print("  Docs:       docs/QUICKSTART.md · docs/BUILDING.md")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())