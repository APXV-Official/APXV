"""Dual proof bundle structures for governance + entity ZK tracks."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_governance_proof_bundle(attested: Dict[str, Any]) -> Dict[str, Any]:
    proofs: Dict[str, Any] = {}
    mapping = {
        "redaction": "zk_proof_redaction",
        "rule_binding": "zk_proof_rule_binding",
        "pipeline": "zk_proof_pipeline",
    }
    for key, legacy_key in mapping.items():
        if legacy_key in attested:
            proofs[key] = attested[legacy_key]
    return {
        "track": "governance",
        "version": "1.1.0",
        "circuits": list(proofs.keys()),
        "proofs": proofs,
    }


def build_entity_proof_bundle(
    entity_proofs: Dict[str, Any],
    *,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "track": "entity",
        "version": "1.0.0",
        "circuits": sorted(entity_proofs.keys()),
        "proofs": entity_proofs,
        "metadata": metadata or {},
    }


def build_dual_proof_bundle(
    attested: Dict[str, Any],
    entity_proofs: Optional[Dict[str, Any]] = None,
    *,
    entity_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    governance = build_governance_proof_bundle(attested)
    entity = build_entity_proof_bundle(
        entity_proofs or attested.get("entity_proofs", {}).get("proofs", {}),
        metadata=entity_metadata or attested.get("entity_proofs", {}).get("metadata"),
    )
    return {
        "version": "1.0.0",
        "governance_proofs": governance,
        "entity_proofs": entity,
    }


def list_entity_circuits(bundle: Dict[str, Any]) -> List[str]:
    entity = bundle.get("entity_proofs", {})
    if isinstance(entity, dict) and "proofs" in entity:
        return list(entity["proofs"].keys())
    if isinstance(entity, dict):
        return [key for key in entity.keys() if key not in {"track", "version", "metadata", "circuits"}]
    return []