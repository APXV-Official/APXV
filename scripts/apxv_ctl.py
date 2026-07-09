"""
APXV — Local Operator Runtime

Air-gapped, self-hosted administration CLI.
No network access required.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

API_KEYS_PATH = ROOT / "managed" / "config" / "api_keys.json"

from agents.auth import APIKeyAuth
from agents.runtime import APXVRuntime
from agents.audit_logger import AuditLogger
from agents.capability_policy import CapabilityPolicyError, CapabilityPolicyManager
from agents.governance_approval import GovernanceApprovalError
from agents.backup_restore import BackupRestoreError, BackupManager
from agents.pack_install import PackInstallError, activate_pack, clone_pack, install_pack
from agents.pack_catalog import list_packs
from agents.pipeline_service import run_pipeline_quiet


def cmd_status(_args: argparse.Namespace) -> int:
    runtime = APXVRuntime()
    print(json.dumps(runtime.get_status(), indent=2))
    return 0 if runtime.verify_integrity()["healthy"] else 1


def cmd_audit_verify(_args: argparse.Namespace) -> int:
    audit_dir = ROOT / "managed" / "audit"
    all_ok = True
    for log_path in sorted(audit_dir.glob("*.log")):
        logger = AuditLogger(log_path=log_path)
        valid = logger.verify_chain()
        print(f"{log_path.name}: {'VALID' if valid else 'INVALID'}")
        all_ok = all_ok and valid
    return 0 if all_ok else 1


def cmd_store_verify(_args: argparse.Namespace) -> int:
    runtime = APXVRuntime()
    result = runtime.store.verify_artifact_chain()
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


def cmd_governance(_args: argparse.Namespace) -> int:
    runtime = APXVRuntime()
    print(json.dumps(runtime.governance.get_status(), indent=2))
    return 0


def cmd_capabilities(_args: argparse.Namespace) -> int:
    runtime = APXVRuntime()
    checker = runtime.capability_checker
    payload = {
        "policy_verified": checker.is_policy_trusted(),
        "policy_version": checker.get_status().get("policy_version"),
        "content_hash": checker.get_status().get("policy_content_hash"),
        "agents": {
            agent_id: sorted(caps)
            for agent_id, caps in checker._agent_capabilities.items()
        },
    }
    print(json.dumps(payload, indent=2))
    return 0 if checker.is_policy_trusted() else 1


def cmd_policy_verify(_args: argparse.Namespace) -> int:
    manager = CapabilityPolicyManager(ROOT)
    try:
        document = manager.load_policy()
        result = manager.verify_document(document)
        print(json.dumps(result, indent=2))
        print("\nCapability policy signature: VALID")
        return 0
    except CapabilityPolicyError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, indent=2))
        print(f"\nCapability policy signature: INVALID ({exc})")
        return 1


def cmd_policy_sign(args: argparse.Namespace) -> int:
    runtime = APXVRuntime()
    checker = runtime.capability_checker
    try:
        if args.migrate:
            manager = CapabilityPolicyManager(ROOT)
            migrated = manager.migrate_legacy_policy()
            if migrated is None:
                print("No unsigned legacy policy to migrate.")
                return 1
            if migrated.get("private_key_pem"):
                print("NEW CAPABILITY SIGNING KEY (save this PEM — shown once):")
                print(migrated["private_key_pem"])
                print()
            print(json.dumps(migrated["signed_policy"], indent=2))
            return 0

        signed = checker.publish_policy(
            issued_by=args.issued_by,
            description=args.description,
        )
        print(json.dumps(signed, indent=2))
        return 0
    except CapabilityPolicyError as exc:
        print(f"Policy signing failed: {exc}")
        return 1


def cmd_governance_proposals(_args: argparse.Namespace) -> int:
    runtime = APXVRuntime()
    print(json.dumps({"proposals": runtime.governance.list_proposals()}, indent=2))
    return 0


def cmd_governance_propose(args: argparse.Namespace) -> int:
    runtime = APXVRuntime()
    content = Path(args.file).read_text(encoding="utf-8") if args.file else args.content
    if not content:
        print("Provide --file or --content")
        return 1
    try:
        result = runtime.governance.propose_change(
            spec_type=args.spec,
            content=content,
            proposed_by=args.proposed_by,
            summary=args.summary,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (GovernanceApprovalError, ValueError) as exc:
        print(f"Proposal failed: {exc}")
        return 1


def cmd_governance_approve(args: argparse.Namespace) -> int:
    runtime = APXVRuntime()
    try:
        result = runtime.governance.approve_proposal(
            args.proposal_id,
            approved_by=args.approved_by,
        )
        if result.get("approval", {}).get("signature") and args.show_signing_key:
            signer_id, pem = runtime.governance.approval.signing.ensure_signing_keypair()
            if pem:
                print("NEW GOVERNANCE SIGNING KEY (save this PEM — shown once):")
                print(pem)
                print()
        print(json.dumps(result, indent=2))
        return 0
    except GovernanceApprovalError as exc:
        print(f"Approval failed: {exc}")
        return 1


def cmd_governance_reject(args: argparse.Namespace) -> int:
    runtime = APXVRuntime()
    try:
        result = runtime.governance.reject_proposal(
            args.proposal_id,
            rejected_by=args.rejected_by,
            reason=args.reason,
        )
        print(json.dumps(result, indent=2))
        return 0
    except GovernanceApprovalError as exc:
        print(f"Rejection failed: {exc}")
        return 1


def cmd_governance_apply(args: argparse.Namespace) -> int:
    runtime = APXVRuntime()
    try:
        result = runtime.governance.apply_proposal(args.proposal_id)
        print(json.dumps(result, indent=2))
        return 0
    except GovernanceApprovalError as exc:
        print(f"Apply failed: {exc}")
        return 1


def cmd_backup_create(args: argparse.Namespace) -> int:
    runtime = APXVRuntime()
    output = Path(args.output) if args.output else None
    try:
        result = runtime.backup_manager.create_backup(output)
        print(json.dumps(result, indent=2))
        return 0
    except BackupRestoreError as exc:
        print(f"Backup failed: {exc}")
        return 1


def cmd_backup_list(_args: argparse.Namespace) -> int:
    runtime = APXVRuntime()
    print(json.dumps({"backups": runtime.backup_manager.list_backups()}, indent=2))
    return 0


def cmd_backup_verify(args: argparse.Namespace) -> int:
    runtime = APXVRuntime()
    try:
        result = runtime.backup_manager.verify_backup(Path(args.archive))
        print(json.dumps(result, indent=2))
        return 0 if result["valid"] else 1
    except BackupRestoreError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, indent=2))
        return 1


def cmd_pack_list(_args: argparse.Namespace) -> int:
    print(json.dumps({"packs": list_packs(ROOT)}, indent=2))
    return 0


def cmd_pack_install(args: argparse.Namespace) -> int:
    try:
        result = install_pack(ROOT, args.pack_id)
        print(json.dumps(result, indent=2))
        return 0
    except PackInstallError as exc:
        print(f"Pack install failed: {exc}")
        return 1


def cmd_pack_activate(args: argparse.Namespace) -> int:
    runtime = APXVRuntime(base_path=ROOT)
    try:
        result = activate_pack(
            runtime,
            args.pack_id,
            confirm=args.confirm,
            activated_by=args.activated_by,
        )
        print(json.dumps(result, indent=2))
        return 0
    except PackInstallError as exc:
        print(f"Pack activate failed: {exc}")
        return 1


def cmd_pack_run(args: argparse.Namespace) -> int:
    runtime = APXVRuntime(base_path=ROOT)
    try:
        result = run_pipeline_quiet(
            args.input_text,
            args.attest,
            runtime,
            pack=args.pack,
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("final_status") == "ATTESTED" else 1
    except Exception as exc:
        print(f"Pack run failed: {exc}")
        return 1


def cmd_pack_clone(args: argparse.Namespace) -> int:
    try:
        result = clone_pack(
            ROOT,
            args.source_pack_id,
            new_pack_id=args.pack_id,
            name=args.name,
            description=args.description,
        )
        print(json.dumps(result, indent=2))
        return 0
    except PackInstallError as exc:
        print(f"Pack clone failed: {exc}")
        return 1


def cmd_backup_restore(args: argparse.Namespace) -> int:
    runtime = APXVRuntime()
    try:
        result = runtime.backup_manager.restore_backup(
            Path(args.archive),
            dry_run=args.dry_run,
            create_safety_backup=not args.no_safety_backup,
        )
        print(json.dumps(result, indent=2))
        return 0
    except BackupRestoreError as exc:
        print(f"Restore failed: {exc}")
        return 1


def cmd_api_key_list(_args: argparse.Namespace) -> int:
    auth = APIKeyAuth(API_KEYS_PATH)
    print(json.dumps({"keys": auth.list_keys()}, indent=2))
    return 0


def cmd_api_key_create(args: argparse.Namespace) -> int:
    auth = APIKeyAuth(API_KEYS_PATH)
    try:
        raw = auth.create_key(
            args.key_id,
            description=args.description,
            role=args.role,
        )
    except ValueError as exc:
        print(f"API key creation failed: {exc}")
        return 1

    hint = None
    if args.save_hint:
        hint = APIKeyAuth.write_key_hint(ROOT, args.key_id, raw)

    print(json.dumps(
        {
            "id": args.key_id,
            "api_key": raw,
            "hint_file": str(hint) if hint else None,
            "message": "Save this key now — it cannot be retrieved later.",
        },
        indent=2,
    ))
    return 0


def cmd_integrity(args: argparse.Namespace) -> int:
    base_path = getattr(args, "base_path", None) or ROOT
    runtime = APXVRuntime(base_path=base_path)
    result = runtime.verify_integrity()
    print(json.dumps(result, indent=2))
    if result["healthy"]:
        print("\nAPX integrity check: HEALTHY")
        return 0
    print("\nAPX integrity check: FAILED")
    for log_name, summary in (result.get("audit_summary") or {}).items():
        if summary.get("issue"):
            print(
                f"  {log_name}: {summary['issue']} "
                f"(corrupt_lines={summary.get('corrupt_line_count', 0)}, "
                f"chain_valid={summary.get('chain_valid')})"
            )
    for hint in result.get("recovery_hints") or []:
        print(f"  -> {hint}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="APXV local operator console (air-gapped)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Runtime and store status")
    sub.add_parser("audit-verify", help="Verify all audit log chains")
    sub.add_parser("store-verify", help="Verify artifact store chain")
    sub.add_parser("governance", help="Show active governance specifications")
    sub.add_parser("governance-proposals", help="List governance change proposals")
    gov_propose = sub.add_parser("governance-propose", help="Propose a governance spec change")
    gov_propose.add_argument("--spec", required=True, choices=["rule", "workflow", "knowledge"])
    gov_propose.add_argument("--file", help="Path to proposed markdown content")
    gov_propose.add_argument("--content", help="Inline proposed markdown content")
    gov_propose.add_argument("--proposed-by", default="operator")
    gov_propose.add_argument("--summary", default="")
    gov_approve = sub.add_parser("governance-approve", help="Approve a governance proposal")
    gov_approve.add_argument("proposal_id")
    gov_approve.add_argument("--approved-by", default="operator")
    gov_approve.add_argument("--show-signing-key", action="store_true")
    gov_reject = sub.add_parser("governance-reject", help="Reject a governance proposal")
    gov_reject.add_argument("proposal_id")
    gov_reject.add_argument("--rejected-by", default="operator")
    gov_reject.add_argument("--reason", default="")
    gov_apply = sub.add_parser("governance-apply", help="Apply an approved governance proposal")
    gov_apply.add_argument("proposal_id")
    sub.add_parser("capabilities", help="Show signed capability policy")
    policy_verify = sub.add_parser("policy-verify", help="Verify capability policy signature")
    policy_sign = sub.add_parser("policy-sign", help="Sign and publish capability policy")
    policy_sign.add_argument(
        "--migrate",
        action="store_true",
        help="Migrate unsigned capabilities.json to signed format",
    )
    policy_sign.add_argument("--issued-by", default="operator", help="Policy issuer label")
    policy_sign.add_argument(
        "--description",
        default="Signed via apxv_ctl",
        help="Human-readable policy change description",
    )
    backup_create = sub.add_parser("backup-create", help="Create managed/ + ZK keys backup")
    backup_create.add_argument("--output", help="Output .tar.gz path (default: managed/backups/)")
    sub.add_parser("backup-list", help="List local backup archives")
    backup_verify = sub.add_parser("backup-verify", help="Verify backup archive integrity")
    backup_verify.add_argument("archive", help="Path to .tar.gz backup")
    backup_restore = sub.add_parser("backup-restore", help="Restore from verified backup")
    backup_restore.add_argument("archive", help="Path to .tar.gz backup")
    backup_restore.add_argument("--dry-run", action="store_true")
    backup_restore.add_argument(
        "--no-safety-backup",
        action="store_true",
        help="Skip pre-restore safety backup",
    )
    integrity = sub.add_parser("integrity", help="Full integrity check (store + audit)")
    integrity.add_argument(
        "--base-path",
        type=Path,
        default=ROOT,
        help="APX project root (default: package root)",
    )

    pack = sub.add_parser("pack", help="Agent pack catalog and activation")
    pack_sub = pack.add_subparsers(dest="pack_command", required=True)
    pack_sub.add_parser("list", help="List installed packs")
    pack_install = pack_sub.add_parser("install", help="Verify pack is present in catalog")
    pack_install.add_argument("pack_id", help="Pack id (e.g. apxv-pack-reference-redaction)")
    pack_activate = pack_sub.add_parser("activate", help="Activate pack governance profile")
    pack_activate.add_argument("pack_id")
    pack_activate.add_argument("--confirm", action="store_true", help="Allow non-official pack")
    pack_activate.add_argument("--activated-by", default="operator")
    pack_run = pack_sub.add_parser("run", help="Run pipeline for a pack")
    pack_run.add_argument("--pack", default="reference")
    pack_run.add_argument("--input-text", default=None)
    pack_run.add_argument("--attest", action="store_true")
    pack_clone = pack_sub.add_parser("clone", help="Clone a pack to a new id")
    pack_clone.add_argument("source_pack_id")
    pack_clone.add_argument("pack_id", help="New apxv-pack-<slug> id")
    pack_clone.add_argument("--name", required=True)
    pack_clone.add_argument("--description", default="")

    api_key = sub.add_parser("api-key", help="Operator API key management")
    api_sub = api_key.add_subparsers(dest="api_command", required=True)
    api_sub.add_parser("list", help="List API key ids (no secrets)")
    api_create = api_sub.add_parser("create", help="Create a new API key")
    api_create.add_argument("key_id", help="Unique key id (e.g. my-app)")
    api_create.add_argument("--description", default="")
    api_create.add_argument("--role", default="operator")
    api_create.add_argument(
        "--save-hint",
        action="store_true",
        default=True,
        help="Write OPERATOR-KEY-<id>.txt under managed/config/ (default: on)",
    )
    api_create.add_argument(
        "--no-save-hint",
        action="store_false",
        dest="save_hint",
        help="Do not write hint file",
    )

    args = parser.parse_args()
    handlers = {
        "status": cmd_status,
        "audit-verify": cmd_audit_verify,
        "store-verify": cmd_store_verify,
        "governance": cmd_governance,
        "governance-proposals": cmd_governance_proposals,
        "governance-propose": cmd_governance_propose,
        "governance-approve": cmd_governance_approve,
        "governance-reject": cmd_governance_reject,
        "governance-apply": cmd_governance_apply,
        "capabilities": cmd_capabilities,
        "policy-verify": cmd_policy_verify,
        "policy-sign": cmd_policy_sign,
        "backup-create": cmd_backup_create,
        "backup-list": cmd_backup_list,
        "backup-verify": cmd_backup_verify,
        "backup-restore": cmd_backup_restore,
        "integrity": cmd_integrity,
    }
    if args.command == "pack":
        pack_handlers = {
            "list": cmd_pack_list,
            "install": cmd_pack_install,
            "activate": cmd_pack_activate,
            "run": cmd_pack_run,
            "clone": cmd_pack_clone,
        }
        return pack_handlers[args.pack_command](args)
    if args.command == "api-key":
        api_handlers = {
            "list": cmd_api_key_list,
            "create": cmd_api_key_create,
        }
        return api_handlers[args.api_command](args)
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())