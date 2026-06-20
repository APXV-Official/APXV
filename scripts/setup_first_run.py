"""
APX v1 — First-Run Setup

Bootstraps a fresh local, air-gapped APX instance:
- Directory structure
- Signed capability policy
- Governance spec bootstrap
- Operator API key
- Server config
- ZK circuit setup (required by default)
- Integrity verification
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.auth import APIKeyAuth
from agents.capability_policy import CapabilityPolicyError, CapabilityPolicyManager
from agents.local_api import DEFAULT_SERVER_CONFIG
from agents.runtime import APXRuntime

DEFAULT_AGENTS = {
    "APX-AGENT-001": ["read_specification", "write_artifact", "execute_agent"],
    "APX-AGENT-002": ["read_specification", "write_artifact", "execute_agent"],
    "APX-AGENT-003": [
        "read_specification",
        "write_artifact",
        "execute_agent",
        "verify_attestation",
    ],
    "APX-AGENT-LLM-001": ["read_specification", "write_artifact", "execute_agent"],
    "APX-AGENT-TOOL-001": ["read_specification", "write_artifact", "execute_agent"],
}

RUNTIME_DIRS = (
    "managed/artifacts",
    "managed/audit",
    "managed/backups",
    "managed/config",
    "managed/store/blobs",
    "rust/apx-circuits/keys",
    "rust/apx-zk/keys",
)


def ensure_directories(base_path: Path) -> None:
    for rel in RUNTIME_DIRS:
        (base_path / rel).mkdir(parents=True, exist_ok=True)


def ensure_capability_policy(base_path: Path) -> dict:
    config_dir = base_path / "managed" / "config"
    policy_path = config_dir / "capabilities.json"
    manager = CapabilityPolicyManager(base_path)
    manager.paths["policy"] = policy_path
    result = {"created": False, "signing_key_shown": False}

    needs_policy = True
    if policy_path.exists():
        try:
            document = manager.load_policy()
            manager.verify_document(document)
            needs_policy = False
            result["status"] = "existing policy verified"
        except CapabilityPolicyError:
            needs_policy = True

    if needs_policy:
        signer_id, private_pem = manager.ensure_signing_keypair()
        document = manager.build_policy_document(
            DEFAULT_AGENTS,
            description="Initial signed capability policy (first-run setup)",
        )
        signed = manager.sign_document(document, signer_id=signer_id)
        policy_path.write_text(json.dumps(signed, indent=2), encoding="utf-8")
        result["created"] = True
        result["status"] = "signed capability policy created"
        if private_pem:
            result["capability_signing_key_pem"] = private_pem
            result["signing_key_shown"] = True

    return result


def ensure_server_config(base_path: Path) -> dict:
    config_path = base_path / "managed" / "config" / "server.json"
    if config_path.exists():
        return {"created": False, "path": str(config_path)}
    config_path.write_text(json.dumps(DEFAULT_SERVER_CONFIG, indent=2), encoding="utf-8")
    return {"created": True, "path": str(config_path)}


def ensure_api_key(base_path: Path) -> dict:
    config_path = base_path / "managed" / "config" / "api_keys.json"
    auth = APIKeyAuth(config_path)
    raw_key = auth.ensure_default_key()
    return {
        "created": raw_key is not None,
        "api_key": raw_key,
    }


def verify_zk_keys(base_path: Path) -> dict:
    keys_dir = base_path / "rust" / "keys"
    circuits = ("redaction", "rule-binding", "pipeline")
    status = {}
    all_ready = True
    for circuit in circuits:
        pk_ok = (keys_dir / f"{circuit}.pk").exists()
        vk_ok = (keys_dir / f"{circuit}.vk").exists()
        ready = pk_ok and vk_ok
        status[circuit] = {"pk": pk_ok, "vk": vk_ok, "ready": ready}
        all_ready = all_ready and ready
    return {"circuits": status, "ready": all_ready}


def run_setup(base_path: Path, *, setup_zk: bool = True) -> dict:
    report = {"base_path": str(base_path), "steps": {}}

    ensure_directories(base_path)
    report["steps"]["directories"] = "ok"

    report["steps"]["capability_policy"] = ensure_capability_policy(base_path)
    report["steps"]["server_config"] = ensure_server_config(base_path)

    runtime = APXRuntime(base_path=base_path)
    report["steps"]["governance_bootstrap"] = runtime.governance.approval.bootstrap_active_specs_if_needed()

    report["steps"]["api_key"] = ensure_api_key(base_path)

    if setup_zk:
        from scripts.setup_zk import ensure_zk_setup

        report["steps"]["zk_setup"] = ensure_zk_setup(base_path=base_path)
        report["steps"]["zk_keys"] = verify_zk_keys(base_path)
    else:
        report["steps"]["zk_setup"] = {"skipped": True}
        report["steps"]["zk_keys"] = verify_zk_keys(base_path)

    integrity = runtime.verify_integrity()
    report["integrity"] = integrity
    zk_ready = report["steps"]["zk_keys"]["ready"]
    report["healthy"] = integrity["healthy"] and (zk_ready or not setup_zk)
    report["zk_required"] = setup_zk
    return report


def print_report(report: dict) -> None:
    print("=" * 60)
    print("APX First-Run Setup")
    print("=" * 60)
    print(f"Base path: {report['base_path']}")
    print()

    cap = report["steps"]["capability_policy"]
    print(f"Capability policy: {cap.get('status', 'ok')}")
    if cap.get("capability_signing_key_pem"):
        print()
        print("NEW CAPABILITY SIGNING KEY (save this PEM — shown once):")
        print(cap["capability_signing_key_pem"])

    api = report["steps"]["api_key"]
    if api.get("api_key"):
        print()
        print("NEW API KEY (save this — shown once):")
        print(f"  {api['api_key']}")
        print("  Use: Authorization: Bearer <key>")

    bootstrapped = report["steps"].get("governance_bootstrap", [])
    if bootstrapped:
        print()
        print(f"Governance specs bootstrapped: {len(bootstrapped)}")

    zk = report["steps"].get("zk_setup", {})
    zk_keys = report["steps"].get("zk_keys", {})
    if zk.get("skipped"):
        print()
        print("ZK setup: skipped (--skip-zk). Attestation will not work until keys exist.")
    elif zk.get("setup_ran"):
        print()
        print("ZK setup: circuit keys generated under rust/apx-circuits/keys/")
    if zk_keys:
        print(f"ZK keys ready: {'yes' if zk_keys.get('ready') else 'no'}")

    print()
    print("Backup these paths regularly:")
    print("  managed/")
    print("  rust/apx-circuits/keys/")
    print("  rust/apx-zk/keys/")
    print()
    print("Integrity check:")
    integrity = report["integrity"]
    status = "HEALTHY" if integrity["healthy"] else "UNHEALTHY"
    print(f"  Status: {status}")
    print(f"  Store chain: {'valid' if integrity['store_chain_valid'] else 'invalid'}")
    print(f"  Capability policy: {'trusted' if integrity['capability_policy_trusted'] else 'untrusted'}")
    print(f"  Governance approvals: {'valid' if integrity['governance_approvals_valid'] else 'invalid'}")
    print()
    print("Next steps:")
    print("  python -m scripts.apx_ctl integrity")
    print("  python -m scripts.apx_serve")
    print("  python -m scripts.run_apx --attest")
    print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description="APX first-run setup (air-gapped)")
    parser.add_argument(
        "--base-path",
        type=Path,
        default=ROOT,
        help="APX base path (default: project root)",
    )
    parser.add_argument(
        "--skip-zk",
        action="store_true",
        help="Skip ZK circuit setup (not recommended — attestation requires keys)",
    )
    args = parser.parse_args()

    try:
        report = run_setup(args.base_path.resolve(), setup_zk=not args.skip_zk)
        print_report(report)
        return 0 if report["healthy"] else 1
    except Exception as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())