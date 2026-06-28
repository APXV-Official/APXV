"""Resolve compliance policy ids (1–5) for the compliance entity circuit."""

from __future__ import annotations

from typing import Any, Dict, Optional

DEFAULT_POLICY_SINGLE_DOC = 1
DEFAULT_POLICY_BATCH = 2
DEFAULT_POLICY_AI_GOVERNANCE = 4
VALID_POLICY_IDS = frozenset({1, 2, 3, 4, 5})


def _coerce_policy_id(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        policy_id = int(value)
    except (TypeError, ValueError):
        return None
    if policy_id in VALID_POLICY_IDS:
        return policy_id
    return None


def resolve_compliance_policy_id(attested: Dict[str, Any]) -> Optional[int]:
    """Return compliance policy id when compliance proof should run."""
    proposed = attested.get("proposed_artifact", {})
    if not isinstance(proposed, dict):
        proposed = {}
    output = proposed.get("output", {})
    if not isinstance(output, dict):
        output = {}
    input_block = proposed.get("input", {})
    if not isinstance(input_block, dict):
        input_block = {}

    candidates = (
        output.get("compliance_policy_id"),
        attested.get("compliance_policy_id"),
    )
    batch_manifest = output.get("batch_manifest")
    if isinstance(batch_manifest, dict):
        candidates = (*candidates, batch_manifest.get("compliance_policy_id"))

    for candidate in candidates:
        policy_id = _coerce_policy_id(candidate)
        if policy_id is not None:
            return policy_id

    original_hash = input_block.get("original_hash", "")
    redacted_hash = input_block.get("post_redaction_hash", "")
    if original_hash and redacted_hash and original_hash != redacted_hash:
        return DEFAULT_POLICY_SINGLE_DOC
    return None


def build_compliance_witness(
    *,
    entity_count: int,
    policy_id: int,
    original_hash: str,
    redacted_hash: str,
) -> dict:
    if policy_id not in VALID_POLICY_IDS:
        raise ValueError(f"compliance policy_id must be 1..5, got {policy_id}")
    if entity_count < 1:
        raise ValueError("compliance requires entity_count >= 1")
    if not original_hash or not redacted_hash or original_hash == redacted_hash:
        raise ValueError("compliance requires distinct original and redacted hashes")

    return {
        "entity_count": entity_count,
        "policy_id": policy_id,
        "original_hash": original_hash,
        "redacted_hash": redacted_hash,
    }