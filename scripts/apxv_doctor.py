"""
APXV — Doctor / prerequisite checker

Validates toolchain, ZK keys, policy, governance, and runtime integrity.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.env import get_env
from agents.runtime import APXVRuntime
from scripts.bootstrap.install_json import read_install_json
from scripts.bootstrap.sovereign_check import verify_sovereign_setup
from scripts.bootstrap.constants import ENTITY_CIRCUITS
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
    from scripts.rust_bins import resolve_apxv_circuits_binary, resolve_apxv_zk_binary

    circuits_bin = resolve_apxv_circuits_binary(ROOT) or shutil.which("apxv-circuits")
    zk_bin = resolve_apxv_zk_binary(ROOT) or shutil.which("apxv-zk")
    container = get_env("APXV_CONTAINER_BIND") == "1"
    ok = (cargo and rustc) or (container and circuits_bin and zk_bin)
    return {
        "name": "rust_toolchain",
        "ok": ok,
        "detail": (
            f"cargo={'yes' if cargo else 'no'}, rustc={'yes' if rustc else 'no'}, "
            f"apxv-circuits={'yes' if circuits_bin else 'no'}, apxv-zk={'yes' if zk_bin else 'no'}"
            + (", container=1" if container else "")
        ),
        "required": "cargo + rustc (native) or baked binaries (Docker)",
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
            "required": f"entity: {len(ENTITY_CIRCUITS)} apxv-zk circuits",
        }
    )

    sovereign = verify_sovereign_setup(base_path, require_provenance=True)
    checks.append(
        {
            "name": "sovereign_setup",
            "ok": sovereign["sovereign_ok"],
            "detail": sovereign,
            "required": "install.json provenance + operator-generated keys",
        }
    )

    install = read_install_json(base_path)
    if install:
        ollama = install.get("ollama") or {}
        if ollama.get("enabled") and not ollama.get("verified"):
            checks.append(
                {
                    "name": "ollama_integration",
                    "ok": False,
                    "detail": ollama,
                    "required": "warn",
                }
            )
        voice = install.get("voice") or {}
        if voice.get("enabled") and not voice.get("model"):
            checks.append(
                {
                    "name": "voice_integration",
                    "ok": False,
                    "detail": voice,
                    "required": "warn",
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
        runtime = APXVRuntime(base_path=base_path)
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

    required_ok = all(
        c["ok"] for c in checks if c["required"] not in ("optional", "warn")
    )
    return {"healthy": required_ok, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="APXV doctor — prerequisite and health checks")
    parser.add_argument("--base-path", type=Path, default=ROOT)
    parser.add_argument("--check-llm", action="store_true", help="Also check local Ollama")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    report = run_doctor(args.base_path.resolve(), check_llm=args.check_llm)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print("=" * 60)
        print("APXV Doctor")
        print("=" * 60)
        for check in report["checks"]:
            status = "OK" if check["ok"] else "FAIL"
            print(f"[{status}] {check['name']}: {check.get('detail')}")
        print()
        print("Overall:", "HEALTHY" if report["healthy"] else "NEEDS ATTENTION")
        if not report["healthy"]:
            sovereign_check = next((c for c in report["checks"] if c["name"] == "sovereign_setup"), None)
            if sovereign_check and not sovereign_check.get("ok"):
                print("Fix issues above, then run: python -m scripts.apxv_bootstrap")
            else:
                print("Fix issues above, then run: python -m scripts.setup_first_run")
            integrity_check = next((c for c in report["checks"] if c["name"] == "integrity"), None)
            if integrity_check and not integrity_check.get("ok"):
                detail = integrity_check.get("detail") or {}
                if isinstance(detail, dict):
                    for log_name, summary in (detail.get("audit_summary") or {}).items():
                        if summary.get("issue"):
                            print(
                                f"Audit {log_name}: {summary['issue']} "
                                f"(corrupt={summary.get('corrupt_line_count', 0)}, "
                                f"chain_valid={summary.get('chain_valid')})"
                            )
                    for hint in detail.get("recovery_hints") or []:
                        print(f"  -> {hint}")
        print("=" * 60)
    return 0 if report["healthy"] else 1


if __name__ == "__main__":
    sys.exit(main())