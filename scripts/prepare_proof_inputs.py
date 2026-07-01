"""
APX v1 — Script 2: prepare_proof_inputs.py

This script takes a completed attested_result (from Agent 3 or a saved artifact)
and extracts the exact public inputs required by the three Rust circuits:

- redaction_proof.rs
- rule_binding.rs
- pipeline_attestation.rs

It outputs a clean JSON structure that can be used as input when we wire
the actual ZK proving in Step 7.

All code is original work written for APX v1.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import json
import sys
import hashlib

# Add parent so we can import the provider if needed
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.runtime import APXRuntime


def _proof_commitment(proof_bundle: Optional[Dict[str, Any]]) -> str:
    """Derive a stable commitment hash from a serialized Groth16 proof bundle."""
    if not proof_bundle or "proof_hex" not in proof_bundle:
        return "0" * 64
    return hashlib.sha256(proof_bundle["proof_hex"].encode()).hexdigest()


def prepare_circuit_inputs(
    attested_result: Dict[str, Any],
    redaction_proof: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convert an APX v1 attested_result into the public inputs expected
    by the three circuits created in Step 5.

    Returns a dictionary with three sections:
        - redaction_proof_inputs
        - rule_binding_inputs
        - pipeline_attestation_inputs
    """
    proposed = attested_result.get("proposed_artifact", {})
    governance = attested_result.get("governance_decision", {})
    proof = attested_result.get("proof", {})

    # Common values
    rule_hash = proposed.get("governed_by", {}).get("rule_file_hash", "")
    workflow_hash = proposed.get("governed_by", {}).get("workflow_file_hash", "")
    knowledge_hash = proposed.get("governed_by", {}).get("knowledge_file_hash", "")

    original_hash = proposed.get("input", {}).get("original_hash", "")
    redacted_hash = proposed.get("input", {}).get("post_redaction_hash", "")
    redaction_count = proposed.get("output", {}).get("total_redactions", 0)

    # Governance decision encoded as a hex string for the Rust hex_to_fr helper.
    decision_map = {
        "APPROVED_NO_CHANGES": 0,
        "APPROVED": 1,
        "APPROVED_WITH_REVIEW_FLAG": 2,
    }
    decision_int = decision_map.get(governance.get("decision", ""), 99)
    decision_hex = f"{decision_int:064x}"

    # === Inputs for redaction_proof.rs ===
    redaction_inputs = {
        "original_hash": original_hash,
        "redacted_hash": redacted_hash,
        "redaction_count": redaction_count,
        "note": "These values go to RedactionProofCircuit public inputs",
    }

    # Use the actual redaction proof commitment when available (proof chaining).
    if redaction_proof is None:
        redaction_proof = attested_result.get("zk_proof_redaction")
    redaction_proof_hash = _proof_commitment(redaction_proof)

    # === Inputs for rule_binding.rs ===
    rule_binding_inputs = {
        "rule_hash": rule_hash,
        "redaction_proof_hash": redaction_proof_hash,
        "redaction_count": redaction_count,
        "note": "Binds the redaction to the exact rule used (APX-RULE-001)",
    }

    # === Inputs for pipeline_attestation.rs (top level) ===
    pipeline_inputs = {
        "rule_hash": rule_hash,
        "workflow_hash": workflow_hash,
        "knowledge_hash": knowledge_hash,
        "final_governance_decision": decision_hex,
        "agent_chain_hash": attested_result.get("full_provenance_hash", ""),
        "note": "Full 3-agent pipeline attestation inputs for PipelineAttestationCircuit",
    }

    return {
        "attestation_id": attested_result.get("attestation_id"),
        "redaction_proof_inputs": redaction_inputs,
        "rule_binding_inputs": rule_binding_inputs,
        "pipeline_attestation_inputs": pipeline_inputs,
        "prepared_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def main():
    """CLI: Load latest artifact or accept a path, then output circuit inputs."""
    provider = APXRuntime().provider

    if len(sys.argv) > 1:
        # User passed a path to a specific artifact JSON
        artifact_path = Path(sys.argv[1])
        if not artifact_path.exists():
            print(f"Error: File not found: {artifact_path}")
            sys.exit(1)
        attested = json.loads(artifact_path.read_text(encoding="utf-8"))
        # The provider wraps artifacts, so we may need to unwrap
        if "artifact" in attested:
            attested = attested["artifact"]
    else:
        # Try to find the most recent attested_result artifact
        artifacts_dir = provider.artifacts_path
        candidates = sorted(artifacts_dir.glob("attested_result_pipeline_*.json"), reverse=True)
        if not candidates:
            print("No attested_result artifacts found. Run `python scripts/run_apx.py` first.")
            sys.exit(1)
        latest = candidates[0]
        print(f"Using latest artifact: {latest.name}")
        wrapped = json.loads(latest.read_text(encoding="utf-8"))
        attested = wrapped.get("artifact", wrapped)

    circuit_inputs = prepare_circuit_inputs(attested)

    # Pretty print + also write a file
    output_path = provider.artifacts_path / "circuit_inputs_latest.json"
    output_path.write_text(json.dumps(circuit_inputs, indent=2), encoding="utf-8")

    print("\n=== Prepared Public Inputs for Rust Circuits ===")
    print(json.dumps(circuit_inputs, indent=2))
    print(f"\nAlso written to: {output_path}")


if __name__ == "__main__":
    main()
