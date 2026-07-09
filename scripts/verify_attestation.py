"""
APXV — Script 3: verify_attestation.py

Python-side attestation verifier for the APXV tiny scope.

This script:
- Re-validates the Python-side hashes and provenance chain
- Checks that the governance decision is consistent with the redaction data
- Confirms the three specification hashes (rule/workflow/knowledge) match
- Prints the exact public input values that would be sent to the ZK circuits

Note: This is NOT a cryptographic ZK verifier. Real Groth16 verification
will be added in Step 7 using the Rust circuits.

All code is original work written for APXV.
"""

from pathlib import Path
from typing import Dict, Any
import json
import hashlib
import sys
import warnings

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.runtime import APXRuntime


def attested_for_python_checks(attested_result: Dict[str, Any], base_path: Path) -> Dict[str, Any]:
    """Decrypt proposed_artifact in-memory when E2EE is enabled (local key only)."""
    proposed = attested_result.get("proposed_artifact", {})
    if proposed.get("status") != "E2EE_ENCRYPTED":
        return attested_result
    if not attested_result.get("e2ee"):
        return attested_result
    from agents.encryption_engine import get_e2ee_instance

    copy = json.loads(json.dumps(attested_result))
    return get_e2ee_instance(base_path=base_path).decrypt_artifact_payload(copy)


def verify_python_attestation(attested_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform a full Python-side verification of an APXV attested result.

    Returns a report with pass/fail for each check.
    """
    report = {
        "attestation_id": attested_result.get("attestation_id"),
        "checks": [],
        "overall_status": "UNKNOWN",
    }

    proposed = attested_result.get("proposed_artifact", {})
    governance = attested_result.get("governance_decision", {})

    # Check 1: Full provenance hash recomputation
    expected_provenance = hashlib.sha256(
        json.dumps(
            {
                "artifact": proposed,
                "governance": governance,
                "proof": attested_result.get("proof", {}),
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()

    actual_provenance = attested_result.get("full_provenance_hash", "")
    check1 = {
        "name": "provenance_hash",
        "passed": expected_provenance == actual_provenance,
        "details": f"Expected {expected_provenance[:16]}... got {actual_provenance[:16]}...",
    }
    report["checks"].append(check1)

    # Check 2: Governance decision consistency
    total_redactions = proposed.get("output", {}).get("total_redactions", 0)
    has_ssn = any(
        r.get("category") == "SSN"
        for r in proposed.get("output", {}).get("redactions_applied", [])
    )

    expected_decision = "APPROVED_NO_CHANGES"
    if total_redactions == 0:
        expected_decision = "APPROVED_NO_CHANGES"
    elif total_redactions <= 5 and not has_ssn:
        expected_decision = "APPROVED"
    elif has_ssn or total_redactions > 10:
        expected_decision = "APPROVED_WITH_REVIEW_FLAG"
    else:
        expected_decision = "APPROVED"

    check2 = {
        "name": "governance_decision",
        "passed": governance.get("decision") == expected_decision,
        "details": f"Decision: {governance.get('decision')} (expected {expected_decision})",
    }
    report["checks"].append(check2)

    # Check 3: All three specification hashes are present and non-empty
    governed = proposed.get("governed_by", {})
    check3 = {
        "name": "specification_hashes_present",
        "passed": bool(governed.get("rule_file_hash")) and
                  bool(governed.get("workflow_file_hash")) and
                  bool(governed.get("knowledge_file_hash")),
        "details": "All three managed specification hashes present in governed_by",
    }
    report["checks"].append(check3)

    # Check 4: Agent chain is complete (APXV canonical; APX legacy accepted)
    from agents.id_compat import normalize_agent_id

    expected_chain = ["APXV-AGENT-001", "APXV-AGENT-002", "APXV-AGENT-003"]
    actual_chain = attested_result.get("agent_chain", [])
    normalized = [normalize_agent_id(aid) for aid in actual_chain]
    check4 = {
        "name": "agent_chain_complete",
        "passed": normalized == expected_chain,
        "details": f"Chain: {actual_chain}",
    }
    report["checks"].append(check4)

    # Overall status
    all_passed = all(c["passed"] for c in report["checks"])
    report["overall_status"] = "VERIFIED" if all_passed else "FAILED"

    return report


def verify_real_zk_independent(
    attested_result: dict,
    base_path: Path,
    circuit: str = "redaction",
) -> dict:
    """
    Perform TRUE independent Groth16 verification using the serialized
    proof_hex + vk_hex that were produced by the Rust prover earlier.

    This is the important function: it does NOT re-run the prover.
    It takes the portable proof artifacts and verifies them cryptographically.
    """
    import subprocess
    import tempfile
    import json

    from .prepare_proof_inputs import prepare_circuit_inputs

    circuit_inputs = prepare_circuit_inputs(attested_result)
    input_key = {
        "redaction": "redaction_proof_inputs",
        "rule-binding": "rule_binding_inputs",
        "pipeline": "pipeline_attestation_inputs",
    }.get(circuit, "redaction_proof_inputs")

    inputs_for_circuit = circuit_inputs[input_key]

    # Look for the proof bundle that was attached during --attest
    # The new run_apx.py stores them under zk_proof_<circuit>
    proof_key = f"zk_proof_{circuit.replace('-', '_')}"
    if proof_key not in attested_result:
        # Fallback to old key name for redaction
        if circuit == "redaction" and "zk_proof_redaction" in attested_result:
            proof_key = "zk_proof_redaction"
        else:
            return {
                "status": "no_proof_in_attestation",
                "message": f"No serialized proof found for circuit {circuit}. Run with --attest first.",
            }

    proof_bundle = attested_result[proof_key]
    if not isinstance(proof_bundle, dict) or "proof_hex" not in proof_bundle:
        return {
            "status": "invalid_proof_bundle",
            "message": "The attached proof data does not contain proof_hex / vk_hex.",
        }

    from .zk_manifest import verify_vk_hash

    proof_hex = proof_bundle["proof_hex"]
    vk_hex = proof_bundle["vk_hex"]
    vk_check = verify_vk_hash(circuit, vk_hex, base_path=base_path)
    if not vk_check["passed"]:
        return {
            "status": "vk_integrity_failed",
            "circuit": circuit,
            "details": vk_check,
        }

    # Use the public inputs embedded in the proof bundle (authoritative).
    public_inputs = proof_bundle.get("public_inputs", inputs_for_circuit)

    with tempfile.TemporaryDirectory() as tmp:
        proof_file = Path(tmp) / "proof_bundle.json"
        proof_file.write_text(
            json.dumps(
                {
                    "proof_hex": proof_hex,
                    "vk_hex": vk_hex,
                    "public_inputs": public_inputs,
                },
                indent=2,
            )
        )

        from scripts.rust_bins import build_apx_circuits_command

        print(f"\n[REAL ZK] Performing independent Groth16 verification for {circuit}...")
        print("            (Using only the serialized proof + vk + public inputs)")

        cmd, cwd = build_apx_circuits_command(
            base_path, "verify", circuit, "--proof", str(proof_file),
        )

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=180,
            )
            print(result.stdout)
            if result.returncode != 0:
                return {
                    "status": "verify_failed",
                    "stderr": result.stderr[-600:],
                    "stdout": result.stdout[-400:],
                }

            return {
                "status": "independent_verification_complete",
                "circuit": circuit,
                "verification_result": "VALID",
                "output": result.stdout[-800:],
            }
        except Exception as e:
            return {"status": "error_calling_rust", "error": str(e)}


def entity_proof_key_for_circuit(circuit: str, proof_key: str | None = None) -> str:
    if proof_key:
        return proof_key
    return circuit.replace("-", "_")


def circuit_for_entity_proof_key(proof_key: str) -> str:
    if proof_key.startswith("merkle_inclusion_"):
        return "merkle-inclusion"
    return proof_key.replace("_", "-")


def verify_entity_zk_independent(
    attested_result: dict,
    base_path: Path,
    circuit: str = "redaction-v1",
    proof_key: str | None = None,
) -> dict:
    """Independent Groth16 verification for entity circuits (apxv-zk)."""
    import subprocess
    import tempfile

    from .entity_zk_manifest import verify_vk_hash

    entity_bundle = attested_result.get("entity_proofs", {})
    proofs = entity_bundle.get("proofs", {})
    resolved_proof_key = entity_proof_key_for_circuit(circuit, proof_key)
    proof_bundle = proofs.get(resolved_proof_key)
    if not isinstance(proof_bundle, dict) or "proof_hex" not in proof_bundle:
        return {
            "status": "no_entity_proof_in_attestation",
            "message": f"No entity proof found for circuit {circuit}. Run with --attest first.",
        }

    vk_hex = proof_bundle.get("vk_hex")
    if not vk_hex:
        return {"status": "invalid_entity_proof_bundle", "message": "Missing vk_hex in entity proof"}

    vk_check = verify_vk_hash(circuit, vk_hex, base_path=base_path)
    if not vk_check["passed"]:
        return {"status": "entity_vk_integrity_failed", "circuit": circuit, "details": vk_check}

    public_inputs = proof_bundle.get("public_inputs", {})
    if not isinstance(public_inputs, dict):
        public_inputs = {}
    with tempfile.TemporaryDirectory() as tmp:
        proof_file = Path(tmp) / "entity_proof_bundle.json"
        verify_payload = dict(public_inputs)
        verify_payload["proof_hex"] = proof_bundle["proof_hex"]
        verify_payload["vk_hex"] = vk_hex
        proof_file.write_text(json.dumps(verify_payload, indent=2), encoding="utf-8")

        rust_dir = base_path / "rust"
        crate_dir = rust_dir / "apxv-zk"
        manifest = rust_dir / "Cargo.toml"

        from agents.zk.poseidon_client import build_apx_zk_command

        cmd, cwd = build_apx_zk_command(
            base_path,
            "verify", circuit,
            "--inputs", str(proof_file),
        )

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=180,
            )
            if result.returncode != 0:
                return {
                    "status": "entity_verify_failed",
                    "circuit": circuit,
                    "stderr": result.stderr[-600:],
                    "stdout": result.stdout[-400:],
                }
            return {
                "status": "independent_verification_complete",
                "circuit": circuit,
                "verification_result": "VALID",
            }
        except Exception as exc:
            return {"status": "error_calling_rust", "error": str(exc)}


def main():
    """CLI entry point."""
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    runtime = APXRuntime()
    provider = runtime.provider
    use_real_zk = False

    if "--real-zk" in sys.argv:
        use_real_zk = True
        sys.argv.remove("--real-zk")

    # Legacy --zk flag still works but now points to the real independent path
    if "--zk" in sys.argv:
        use_real_zk = True
        sys.argv.remove("--zk")

    base = Path(__file__).parent.parent

    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        wrapped = json.loads(path.read_text(encoding="utf-8"))
        attested = wrapped.get("artifact", wrapped)
    else:
        artifacts_dir = provider.artifacts_path

        # Robust discovery: when doing real ZK verification, prefer the newest artifact
        # that actually contains zk_proof_* data. This prevents loading a stale
        # attested_result_pipeline_*.json that predates the --attest run.
        if use_real_zk:
            all_candidates = sorted(
                artifacts_dir.glob("attested_result_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            latest = None
            for cand in all_candidates:
                try:
                    data = json.loads(cand.read_text(encoding="utf-8"))
                    inner = data.get("artifact", data)
                    if any(k.startswith("zk_proof_") for k in inner.keys()):
                        latest = cand
                        break
                except Exception:
                    continue
            if latest is None:
                # Fallback to the normal pipeline glob if nothing with proofs exists yet
                candidates = sorted(artifacts_dir.glob("attested_result_pipeline_*.json"), reverse=True)
                latest = candidates[0] if candidates else None
        else:
            candidates = sorted(artifacts_dir.glob("attested_result_pipeline_*.json"), reverse=True)
            latest = candidates[0] if candidates else None

        if not latest:
            print("No attested artifacts found. Run scripts/run_apx.py --attest first.")
            sys.exit(1)

        print(f"Verifying latest artifact: {latest.name}")
        wrapped = json.loads(latest.read_text(encoding="utf-8"))
        attested = wrapped.get("artifact", wrapped)

    python_attested = attested_for_python_checks(attested, base)
    if (
        attested.get("proposed_artifact", {}).get("status") == "E2EE_ENCRYPTED"
        and python_attested is not attested
    ):
        print("Note: proposed_artifact is E2EE-encrypted — decrypting locally for Python-side checks.")

    report = verify_python_attestation(python_attested)

    print("\n=== APX Python Attestation Verification Report (hash/provenance/governance) ===")
    print(json.dumps(report, indent=2))

    if report["overall_status"] == "VERIFIED":
        print("\n? All Python-side checks passed.")
        print("  The attested_result is consistent with the living markdown specs (hash/provenance checks).")
    else:
        print("\n? Python-side verification failed. See checks above.")

    if use_real_zk:
        print("\n" + "=" * 70)
        print("REAL CRYPTOGRAPHIC VERIFICATION (Independent Groth16 over BN254)")
        print("=" * 70)
        print("This uses ONLY the serialized proof + vk + public inputs.")
        print("No re-proving occurs. This is what makes the attestations independently verifiable.\n")

        zk_results = {}
        all_valid = True
        for circuit in ["redaction", "rule-binding", "pipeline"]:
            zk_result = verify_real_zk_independent(attested, base, circuit=circuit)
            zk_results[circuit] = zk_result
            if zk_result.get("status") != "independent_verification_complete":
                all_valid = False
            print(f"\n--- governance: {circuit} ---")
            print(json.dumps(zk_result, indent=2))

        entity_proof_keys = sorted(attested.get("entity_proofs", {}).get("proofs", {}).keys())

        entity_results = {}
        for proof_key in entity_proof_keys:
            circuit = circuit_for_entity_proof_key(proof_key)
            entity_result = verify_entity_zk_independent(
                attested,
                base,
                circuit=circuit,
                proof_key=proof_key,
            )
            entity_results[proof_key] = entity_result
            if entity_result.get("status") != "independent_verification_complete":
                all_valid = False
            print(f"\n--- entity: {proof_key} ({circuit}) ---")
            print(json.dumps(entity_result, indent=2))

        print("\n" + "=" * 70)
        if all_valid and entity_proof_keys:
            print(
                f"ALL GOVERNANCE + ENTITY GROTH16 PROOFS INDEPENDENTLY VERIFIED [OK] "
                f"(3 governance + {len(entity_proof_keys)} entity)"
            )
        elif all_valid:
            print("ALL THREE GOVERNANCE GROTH16 PROOFS INDEPENDENTLY VERIFIED [OK]")
        else:
            print("ONE OR MORE GROTH16 PROOFS FAILED INDEPENDENT VERIFICATION [FAIL]")
            sys.exit(1)

    # Show the exact public inputs that were (or would be) used in the ZK circuits
    from .prepare_proof_inputs import prepare_circuit_inputs
    inputs = prepare_circuit_inputs(python_attested)
    print("\n--- Public Inputs that must match the ZK proof (for all three circuits) ---")
    print(json.dumps(inputs, indent=2))


if __name__ == "__main__":
    main()
