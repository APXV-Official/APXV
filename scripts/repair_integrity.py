"""Repair operator integrity: audit hash chains + governance approval reconcile."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SPEC_MAP = {
    "managed/rules/rule1.md": "rule",
    "managed/workflows/workflow1.md": "workflow",
    "managed/knowledge/knowledge1.md": "knowledge",
}


def resolve_base_path() -> Path:
    env = os.environ.get("APXV_ROOT") or os.environ.get("APXV_BASE_PATH")
    if env:
        return Path(env).resolve()
    return ROOT


def reconcile_governance_specs(base_path: Path) -> list[str]:
    from agents.runtime import APXVRuntime

    runtime = APXVRuntime(base_path=base_path)
    approval = runtime.governance.approval
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    reconciled: list[str] = []

    for rel, spec_type in SPEC_MAP.items():
        spec_path = base_path / rel
        if not spec_path.is_file():
            continue
        active = approval.store.get_active_approval(spec_type)
        current_hash = approval._content_hash(spec_path.read_text(encoding="utf-8"))
        if active and active["content_hash"] == current_hash:
            continue
        approval.store.set_active_approval(
            spec_type=spec_type,
            content_hash=current_hash,
            proposal_id=f"integrity-reconcile-{spec_type}",
            approved_at=now,
            applied_at=now,
        )
        reconciled.append(spec_type)

    return reconciled


def repair_audit(base_path: Path) -> dict[str, object]:
    from agents.runtime import APXVRuntime

    runtime = APXVRuntime(base_path=base_path)
    return runtime.repair_audit_logs()


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair APXV operator integrity")
    parser.add_argument("--base-path", type=Path, default=None)
    parser.add_argument("--audit", action="store_true", help="Rebuild audit log hash chains")
    parser.add_argument(
        "--governance",
        action="store_true",
        help="Reconcile active governance approvals with on-disk specs",
    )
    parser.add_argument("--all", action="store_true", help="Run audit + governance repair")
    args = parser.parse_args()

    base = (args.base_path or resolve_base_path()).resolve()
    do_audit = args.audit or args.all
    do_gov = args.governance or args.all
    if not do_audit and not do_gov:
        do_audit = do_gov = True

    if do_audit:
        result = repair_audit(base)
        print(f"audit repair at {base}: all_valid={result.get('all_valid')}")
        for name, info in (result.get("logs") or {}).items():
            if info.get("repaired"):
                print(f"  repaired {name} (chain_valid={info.get('chain_valid')})")

    if do_gov:
        reconciled = reconcile_governance_specs(base)
        if reconciled:
            print(f"governance reconciled: {', '.join(reconciled)}")
        else:
            print("governance: approvals already match disk")

    from agents.runtime import APXVRuntime

    healthy = APXVRuntime(base_path=base).verify_integrity()["healthy"]
    print(f"integrity healthy: {healthy}")
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())