"""
APXV sovereign bootstrap — single entry point for operator first-run.

    python -m scripts.apxv_bootstrap
    python -m scripts.apxv_bootstrap --base-path /path/to/instance
    python -m scripts.apxv_bootstrap --skip-ollama --skip-voice --json-report

Exit codes:
    0 — healthy (sovereign setup complete)
    1 — sovereign bootstrap failed
    2 — sovereign ok, optional integrations incomplete (Ollama/Vosk)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.bootstrap import BootstrapOptions, run_bootstrap
from scripts.bootstrap.constants import BOOTSTRAP_VERSION


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="APXV sovereign bootstrap — local trusted setup and runtime init"
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        default=ROOT,
        help="APXV instance root (default: runtime project root)",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=ROOT,
        help="Runtime source tree for templates and scripts (default: project root)",
    )
    parser.add_argument(
        "--skip-ollama",
        action="store_true",
        help="Skip Ollama probe (AI Governance pack unavailable until configured)",
    )
    parser.add_argument(
        "--skip-voice",
        action="store_true",
        help="Skip Vosk voice model setup",
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Skip post-bootstrap smoke (developer/CI only)",
    )
    parser.add_argument(
        "--skip-prover-build",
        action="store_true",
        help="Do not run cargo build when binaries are missing (CI/tests)",
    )
    parser.add_argument(
        "--profile",
        choices=("production", "ci"),
        default="production",
        help="Install profile written to runtime.json and install.json",
    )
    parser.add_argument(
        "--json-report",
        action="store_true",
        help="Print full bootstrap report as JSON on stdout",
    )
    args = parser.parse_args(argv)

    base_path = args.base_path.resolve()
    prev_base = os.environ.get("APXV_BASE_PATH")
    prev_profile = os.environ.get("APXV_PROFILE")
    os.environ["APXV_BASE_PATH"] = str(base_path)
    if args.profile == "ci":
        os.environ["APXV_PROFILE"] = "ci"

    print("=" * 60)
    print(f"APXV Sovereign Bootstrap v{BOOTSTRAP_VERSION}")
    print("=" * 60)
    print(f"Base path: {base_path}")
    print(f"Profile:   {args.profile}")
    print()

    options = BootstrapOptions(
        base_path=base_path,
        source_root=args.source_root.resolve(),
        skip_ollama=args.skip_ollama,
        skip_voice=args.skip_voice,
        skip_smoke=args.skip_smoke,
        skip_prover_build=args.skip_prover_build,
        profile=args.profile,
        json_report=args.json_report,
    )

    try:
        report = run_bootstrap(options)
    finally:
        if prev_base is None:
            os.environ.pop("APXV_BASE_PATH", None)
        else:
            os.environ["APXV_BASE_PATH"] = prev_base
        if prev_profile is None:
            os.environ.pop("APXV_PROFILE", None)
        else:
            os.environ["APXV_PROFILE"] = prev_profile

    if args.json_report:
        print(json.dumps(report.to_dict(), indent=2))
    elif report.ok:
        print()
        print("=" * 60)
        print("Sovereign bootstrap complete")
        print(f"  install.json: {base_path / 'managed' / 'config' / 'install.json'}")
        print(f"  sovereign_setup: {report.sovereign_setup}")
        if report.partial:
            print("  optional integrations: incomplete (exit 2)")
        print("=" * 60)
    else:
        print("Sovereign bootstrap FAILED:", file=sys.stderr)
        for err in report.errors:
            print(f"  - {err}", file=sys.stderr)

    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())