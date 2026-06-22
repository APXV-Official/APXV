"""
APXV1 — ZK ceremony transcript (Tier A/B transparency).

Aggregates governance + entity key manifests into a signed, verifiable document.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.capability_policy import CapabilityPolicyError, CapabilityPolicyManager, _canonical_json
from scripts.entity_zk_manifest import load_manifest as load_entity_manifest
from scripts.zk_manifest import load_manifest as load_governance_manifest

TRANSCRIPT_VERSION = "1.0.0"
DEFAULT_TIER = "B"
TRANSCRIPT_PATH_REL = "managed/config/ceremony-transcript.json"


def transcript_path(base_path: Optional[Path] = None) -> Path:
    base = base_path or ROOT
    return base / TRANSCRIPT_PATH_REL


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _signing_body(document: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in document.items() if k not in ("signature", "content_hash")}


def transcript_content_hash(document: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(_signing_body(document)).encode("utf-8")).hexdigest()


def build_transcript(
    base_path: Optional[Path] = None,
    *,
    ceremony_tier: str = DEFAULT_TIER,
    operator_note: str = "",
    sign: bool = True,
) -> Dict[str, Any]:
    base = base_path or ROOT
    governance = load_governance_manifest(base)
    entity = load_entity_manifest(base)

    document: Dict[str, Any] = {
        "transcript_version": TRANSCRIPT_VERSION,
        "ceremony_tier": ceremony_tier,
        "generated_at": _utcnow(),
        "operator_note": operator_note,
        "governance": governance,
        "entity": entity,
    }
    document["content_hash"] = transcript_content_hash(document)

    if sign:
        manager = CapabilityPolicyManager(base)
        private_key = manager.load_private_key()
        signing_config = manager.load_signing_config()
        if private_key and signing_config:
            signature_bytes = private_key.sign(document["content_hash"].encode("utf-8"))
            document["signature"] = {
                "algorithm": "Ed25519",
                "signer_id": signing_config.get("signer_id", "default-capability-signer"),
                "value": base64.b64encode(signature_bytes).decode("ascii"),
            }
        else:
            document["signature"] = None

    return document


def verify_transcript(
    base_path: Optional[Path] = None,
    *,
    document: Optional[Dict[str, Any]] = None,
    require_signature: bool = False,
) -> Dict[str, Any]:
    base = base_path or ROOT
    path = transcript_path(base)
    doc = document or (
        json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    )
    if not doc:
        return {"valid": False, "reason": f"Missing ceremony transcript: {path}"}

    issues = []
    expected_hash = transcript_content_hash(doc)
    if doc.get("content_hash") != expected_hash:
        issues.append("content_hash mismatch (transcript body tampered)")

    gov = load_governance_manifest(base)
    ent = load_entity_manifest(base)
    if doc.get("governance") != gov:
        issues.append("governance manifest drift (re-run --write after key changes)")
    if doc.get("entity") != ent:
        issues.append("entity manifest drift (re-run --write after key changes)")

    signature = doc.get("signature")
    if require_signature and not signature:
        issues.append("signature required but missing")
    elif signature:
        manager = CapabilityPolicyManager(base)
        try:
            public_key = manager.load_public_key()
            sig_bytes = base64.b64decode(signature["value"])
            public_key.verify(sig_bytes, doc["content_hash"].encode("utf-8"))
        except CapabilityPolicyError as exc:
            issues.append(f"signature present but signer not configured: {exc}")
        except Exception as exc:
            issues.append(f"signature invalid: {exc}")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "path": str(path),
        "ceremony_tier": doc.get("ceremony_tier"),
        "content_hash": doc.get("content_hash"),
    }


def write_transcript(
    base_path: Optional[Path] = None,
    *,
    ceremony_tier: str = DEFAULT_TIER,
    operator_note: str = "",
    sign: bool = True,
) -> Path:
    base = base_path or ROOT
    path = transcript_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = build_transcript(
        base,
        ceremony_tier=ceremony_tier,
        operator_note=operator_note,
        sign=sign,
    )
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="APXV1 ZK ceremony transcript")
    parser.add_argument("--base-path", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true", help="Generate transcript from current manifests")
    parser.add_argument("--verify", action="store_true", help="Verify transcript against on-disk manifests")
    parser.add_argument("--tier", default=DEFAULT_TIER, choices=["A", "B", "C"])
    parser.add_argument("--note", default="", help="Operator note stored in transcript")
    parser.add_argument("--no-sign", action="store_true", help="Tier A: omit Ed25519 signature")
    parser.add_argument("--require-signature", action="store_true", help="Fail verify if unsigned")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    base = args.base_path.resolve()

    if args.write:
        path = write_transcript(
            base,
            ceremony_tier=args.tier,
            operator_note=args.note,
            sign=not args.no_sign,
        )
        result = verify_transcript(base, require_signature=args.require_signature)
        if args.json:
            print(json.dumps({"written": str(path), "verify": result}, indent=2))
        else:
            print(f"Ceremony transcript written: {path}")
            print(f"Verify: {'OK' if result['valid'] else 'FAILED'}")
            if result.get("issues"):
                for issue in result["issues"]:
                    print(f"  - {issue}")
        return 0 if result["valid"] else 1

    if args.verify:
        result = verify_transcript(base, require_signature=args.require_signature)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            status = "OK" if result["valid"] else "FAILED"
            print(f"Ceremony transcript verify: {status}")
            if result.get("issues"):
                for issue in result["issues"]:
                    print(f"  - {issue}")
        return 0 if result["valid"] else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())