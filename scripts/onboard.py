"""
APXV1 onboarding — setup, pack demo, attest, and independent verify.

    python -m scripts.onboard
    python -m scripts.onboard --pack document
    python -m scripts.onboard --pack all

Used by install.ps1 / install.sh. In Docker (ZK keys baked in image):

    python -m scripts.onboard --skip-zk
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent.parent

PACK_CHOICES = ("reference", "document", "ai", "all")

PACK_LABELS = {
    "reference": "Reference Redaction Pack demo",
    "document": "Document Processing Pack demo",
    "ai": "AI Governance Pack demo",
}


def _pack_demo_path(pack: str) -> Path:
    mapping = {
        "reference": ROOT
        / "governance-libraries"
        / "apxv-pack-reference-redaction"
        / "examples"
        / "run_pack_demo.py",
        "document": ROOT
        / "governance-libraries"
        / "apxv-pack-document-processing"
        / "examples"
        / "run_pack_demo.py",
        "ai": ROOT
        / "governance-libraries"
        / "apxv-pack-ai-governance"
        / "examples"
        / "run_pack_demo.py",
    }
    return mapping[pack]


def resolve_pack_runs(pack: str) -> List[Tuple[str, Path]]:
    if pack == "all":
        return [
            ("reference", _pack_demo_path("reference")),
            ("document", _pack_demo_path("document")),
            ("ai", _pack_demo_path("ai")),
        ]
    return [(pack, _pack_demo_path(pack))]


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
    parser.add_argument(
        "--pack",
        choices=PACK_CHOICES,
        default="reference",
        help="Pack demo to run (default: reference). 'all' runs every official pack.",
    )
    args = parser.parse_args()

    pack_runs = resolve_pack_runs(args.pack)
    for _name, demo_path in pack_runs:
        if not demo_path.is_file():
            print(f"ERROR: pack demo not found: {demo_path}", file=sys.stderr)
            return 1

    py = sys.executable
    total = len(pack_runs) + 4 + (0 if args.skip_setup else 1)
    step = 1

    pack_title = args.pack if args.pack != "all" else "all official packs"
    print("=" * 60)
    print("APXV1 onboarding")
    print(f"Pack demo: {pack_title} → attest → verify")
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

    for pack_name, demo_path in pack_runs:
        _run(PACK_LABELS[pack_name], [py, str(demo_path)], step=step, total=total)
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
    if args.pack == "reference":
        print("  Pack demo:  final_status=ATTESTED, total_redactions=4")
    elif args.pack == "document":
        print("  Pack demo:  final_status=ATTESTED, file_count=2, compliance_policy_id=2")
    elif args.pack == "ai":
        print("  Pack demo:  final_status=ATTESTED, compliance_policy_id=4")
    else:
        print("  Pack demos: reference + document + ai (see output above)")
    print("  Quick redo: python -m scripts.apx_demo --pack", args.pack)
    print("  Next:       python -m scripts.apx_serve")
    print("  Docs:       docs/QUICKSTART.md · docs/BUILDING.md")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())