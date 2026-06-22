"""
APX v1 — Doctor / prerequisite checker

Validates toolchain, ZK keys, policy, governance, and runtime integrity.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.runtime import APXRuntime
from scripts.setup_first_run import verify_entity_zk_keys, verify_zk_keys


def _check_python() -> dict:
    major, minor = sys.version_info[:2]
    ok = (major, minor) >= (3, 9)
    return {
        "name": "python",
        "ok": ok,
        "detail": f"{major}.{minor}",
        "required": "3.9+",
    }


def _check_command(name: str) -> bool:
    return shutil.which(name) is not None


def _check_rust() -> dict:
    cargo = _check_command("cargo")
    rustc = _check_command("rustc")
    from scripts.rust_bins import resolve_apx_circuits_binary, resolve_apx_zk_binary

    circuits_bin = resolve_apx_circuits_binary(ROOT) or shutil.which("apx-circuits")
    zk_bin = resolve_apx_zk_binary(ROOT) or shutil.which("apx-zk")
    ok = cargo and rustc
    return {
        "name": "rust_toolchain",
        "ok": ok,
        "detail": (
            f"cargo={'yes' if cargo else 'no'}, rustc={'yes' if rustc else 'no'}, "
            f"apx-circuits={'yes' if circuits_bin else 'no'}, apx-zk={'yes' if zk_bin else 'no'}"
        ),
        "required": "cargo + rustc (for ZK setup and proofs)",
    }


def _check_ollama(optional: bool) -> dict:
    if not optional:
        return {"name": "ollama", "ok": True, "detail": "skipped", "required": "optional"}
    try:
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as resp:
            ok = resp.status == 200
    except Exception as exc:
        ok = False
        detail = str(exc)
    else:
        detail = "reachable on 127.0.0.1:11434"
    return {
        "name": "ollama",
        "ok": ok,
        "detail": detail,
        "required": "optional (--check-llm)",
    }


def run_doctor(base_path: Path, *, check_llm: bool = False) -> dict:
    checks = [
        _check_python(),
        _check_rust(),
        _check_ollama(check_llm),
    ]

    zk = verify_zk_keys(base_path)
    checks.append(
        {
            "name": "zk_keys_governance",
            "ok": zk["ready"],
            "detail": zk["circuits"],
            "required": "governance: redaction, rule-binding, pipeline",
        }
    )
    entity_zk = verify_entity_zk_keys(base_path)
    checks.append(
        {
            "name": "zk_keys_entity",
            "ok": entity_zk["ready"],
            "detail": entity_zk["circuits"],
            "required": "entity: 8 apx-zk circuits",
        }
    )

    policy_path = base_path / "managed" / "config" / "capabilities.json"
    if not policy_path.exists():
        checks.append(
            {
                "name": "capability_policy",
                "ok": False,
                "detail": "missing — run: python -m scripts.setup_first_run",
                "required": "signed capabilities.json",
            }
        )
        integrity = {"healthy": False}
    else:
        runtime = APXRuntime(base_path=base_path)
        integrity = runtime.verify_integrity()
        checks.append(
            {
                "name": "capability_policy",
                "ok": integrity.get("capability_policy_trusted", False),
                "detail": runtime.capability_checker.get_status(),
                "required": "signed trusted policy",
            }
        )
        checks.append(
            {
                "name": "integrity",
                "ok": integrity.get("healthy", False),
                "detail": integrity,
                "required": "store + audit + governance healthy",
            }
        )

    transcript_path = base_path / "managed" / "config" / "ceremony-transcript.json"
    if transcript_path.exists():
        from scripts.ceremony_transcript import verify_transcript

        ceremony = verify_transcript(base_path)
        checks.append(
            {
                "name": "ceremony_transcript",
                "ok": ceremony.get("valid", False),
                "detail": ceremony.get("issues") or ceremony.get("ceremony_tier"),
                "required": "signed VK lineage matches manifests",
            }
        )

    required_ok = all(c["ok"] for c in checks if c["required"] != "optional")
    return {"healthy": required_ok, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="APX doctor — prerequisite and health checks")
    parser.add_argument("--base-path", type=Path, default=ROOT)
    parser.add_argument("--check-llm", action="store_true", help="Also check local Ollama")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    report = run_doctor(args.base_path.resolve(), check_llm=args.check_llm)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print("=" * 60)
        print("APX Doctor")
        print("=" * 60)
        for check in report["checks"]:
            status = "OK" if check["ok"] else "FAIL"
            print(f"[{status}] {check['name']}: {check.get('detail')}")
        print()
        print("Overall:", "HEALTHY" if report["healthy"] else "NEEDS ATTENTION")
        if not report["healthy"]:
            print("Fix issues above, then run: python -m scripts.setup_first_run")
            integrity_check = next((c for c in report["checks"] if c["name"] == "integrity"), None)
            if integrity_check and not integrity_check.get("ok"):
                detail = integrity_check.get("detail") or {}
                audit_logs = detail.get("audit_logs") if isinstance(detail, dict) else {}
                if isinstance(audit_logs, dict) and audit_logs and not all(audit_logs.values()):
                    print(
                        "Audit chain broken (often from local testing)? "
                        "Remove managed/audit/ and re-run: python -m scripts.setup_first_run"
                    )
        print("=" * 60)
    return 0 if report["healthy"] else 1


if __name__ == "__main__":
    sys.exit(main())