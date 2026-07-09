"""Programmatic attestation verification for API v2."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from scripts.verify_attestation import (
    attested_for_python_checks,
    circuit_for_entity_proof_key,
    entity_proof_key_for_circuit,
    verify_entity_zk_independent,
    verify_python_attestation,
    verify_real_zk_independent,
)


def verify_attestation_artifact(
    attested: Dict[str, Any],
    *,
    base_path: Path,
    real_zk: bool = True,
) -> Dict[str, Any]:
    """Run Python-side checks and optional independent Groth16 verification."""
    python_checked = attested_for_python_checks(attested, base_path)
    python_report = verify_python_attestation(python_checked)

    result: Dict[str, Any] = {
        "attestation_id": attested.get("attestation_id"),
        "python": python_report,
        "zk": None,
        "overall_valid": python_report.get("overall_status") == "VERIFIED",
    }

    if not real_zk:
        return result

    zk_reports: Dict[str, Any] = {"governance": {}, "entity": {}}
    all_valid = python_report.get("overall_status") == "VERIFIED"

    for circuit in ("redaction", "rule-binding", "pipeline"):
        report = verify_real_zk_independent(python_checked, base_path, circuit=circuit)
        zk_reports["governance"][circuit] = report
        if report.get("verification_result") is not True:
            all_valid = False

    entity_keys = sorted(attested.get("entity_proofs", {}).get("proofs", {}).keys())
    for proof_key in entity_keys:
        circuit = circuit_for_entity_proof_key(proof_key)
        report = verify_entity_zk_independent(
            python_checked,
            base_path,
            circuit=circuit,
            proof_key=proof_key,
        )
        zk_reports["entity"][proof_key] = report
        if report.get("verification_result") is not True:
            all_valid = False

    result["zk"] = zk_reports
    result["overall_valid"] = all_valid and (
        not entity_keys or all(
            zk_reports["entity"][k].get("verification_result") is True for k in entity_keys
        )
    )
    return result


def load_attested_for_verify(
    *,
    runtime,
    artifact_hash: Optional[str] = None,
    inline: Optional[Dict[str, Any]] = None,
    base_path: Path,
) -> Dict[str, Any]:
    if inline is not None:
        if "artifact" in inline:
            return inline["artifact"]
        return inline
    if not artifact_hash:
        raise ValueError("artifact_hash or inline attestation required")
    data = runtime.provider.read_artifact(artifact_hash)
    return data.get("artifact", data)