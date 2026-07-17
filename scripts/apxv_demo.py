"""
APXV pack demo — pack pipeline, attest, verify, print artifact path.

For instances already initialized (setup_first_run complete).

    python -m scripts.apxv_demo
    python -m scripts.apxv_demo --pack document
    python -m scripts.apxv_demo --pack ai
    python -m scripts.apxv_demo --pack all
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent.parent

PACK_CHOICES = ("reference", "document", "ai", "all")


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
    path = mapping.get(pack)
    if path is None:
        raise ValueError(f"Unknown pack: {pack}")
    return path


def resolve_pack_runs(pack: str) -> List[Tuple[str, Path]]:
    if pack == "all":
        return [
            ("reference", _pack_demo_path("reference")),
            ("document", _pack_demo_path("document")),
            ("ai", _pack_demo_path("ai")),
        ]
    return [(pack, _pack_demo_path(pack))]


def find_latest_zk_artifact(base_path: Path) -> Path | None:
    """Return newest attested artifact that contains zk_proof_* fields."""
    artifacts_dir = base_path / "managed" / "artifacts"
    if not artifacts_dir.is_dir():
        return None

    candidates = sorted(
        artifacts_dir.glob("attested_result_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for cand in candidates:
        try:
            data = json.loads(cand.read_text(encoding="utf-8"))
            inner = data.get("artifact", data)
            if any(k.startswith("zk_proof_") for k in inner.keys()):
                return cand
        except (json.JSONDecodeError, OSError):
            continue

    fallback = sorted(
        artifacts_dir.glob("attested_result_pipeline_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return fallback[0] if fallback else None


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
        description="APXV pack demo — pack pipeline, attest, verify, artifact path"
    )
    parser.add_argument(
        "--pack",
        choices=PACK_CHOICES,
        default="reference",
        help="Which pack demo to run (default: reference). 'all' runs every v1.2 pack.",
    )
    args = parser.parse_args()

    pack_runs = resolve_pack_runs(args.pack)
    for _name, demo_path in pack_runs:
        if not demo_path.is_file():
            print(f"ERROR: pack demo not found: {demo_path}", file=sys.stderr)
            return 1

    total = len(pack_runs) + 2
    py = sys.executable
    step = 1

    print("=" * 60)
    print("APXV pack demo")
    print(f"Pack(s): {args.pack}")
    print("=" * 60)

    pack_labels = {
        "reference": "Reference Redaction Pack demo",
        "document": "Document Processing Pack demo",
        "ai": "AI Governance Pack demo",
    }
    for pack_name, demo_path in pack_runs:
        _run(pack_labels[pack_name], [py, str(demo_path)], step=step, total=total)
        step += 1

    _run(
        "Platform pipeline + attestation",
        [py, "-m", "scripts.run_apxv", "--attest"],
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

    artifact = find_latest_zk_artifact(ROOT)
    print()
    print("=" * 60)
    print("Pack demo complete.")
    if artifact is not None:
        rel = artifact.relative_to(ROOT)
        print(f"  Artifact: {rel}")
        print(f"  Verify:   python -m scripts.verify_attestation --real-zk {rel}")
    else:
        print("  Artifact: (not found under managed/artifacts/)")
    print("  API:      python -m scripts.apxv_serve")
    print("  Docs:     docs/QUICKSTART.md")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())