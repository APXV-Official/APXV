"""
APXV — Script 1: run_apx.py (Main Orchestrator)

This is the primary end-to-end runner for the APXV tiny implementation.

It executes the complete 3-agent pipeline:
    RuleGovernedRedactor (Agent 1)
        â†’ WorkflowOrchestrator (Agent 2)
        â†’ AttestationCoordinator (Agent 3)

Then writes the final attested result as a governed artifact using
the MinimalArtifactProvider and prints a clean summary.

This script demonstrates the "one command to run the full loop" goal
for the current scope.

All code is original work written for APXV.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import hashlib
import json
import sys

# Add parent to path so we can import agents
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.agent1 import RuleGovernedRedactor
from agents.agent2 import WorkflowOrchestrator
from agents.agent3 import AttestationCoordinator
from agents.runtime import APXVRuntime


def prepare_voice_session(
    *,
    base_path: Path,
    voice_file: Optional[Path] = None,
    voice_transcript: Optional[str] = None,
    voice_mode: Optional[str] = None,
    synthesize_tts: bool = False,
) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Run voice STT/redaction; return (pipeline_input_text, voice_session dict)."""
    from agents.voice import VoicePrivacyPipeline

    if not voice_file and not voice_transcript:
        return None, None

    pipeline = VoicePrivacyPipeline(base_path=base_path, voice_mode=voice_mode)
    if voice_file:
        audio = voice_file.read_bytes()
        audio_sha = hashlib.sha256(audio).hexdigest()
        result = pipeline.process_audio(audio, synthesize_redacted=synthesize_tts)
        session = pipeline.build_voice_session(result, source="audio_file", audio_sha256=audio_sha)
        session["audio_path"] = str(voice_file)
    else:
        result = pipeline.process_transcript(voice_transcript or "", synthesize_redacted=synthesize_tts)
        session = pipeline.build_voice_session(result, source="transcript")

    print("\n[Voice] STT + redaction complete")
    print(f"      - Mode: {result.voice_mode} (STT: {result.stt_provider})")
    print(f"      - Entities: {len(result.entities)}")
    print(f"      - Transcript: {result.transcript[:72]}...")

    # Feed original transcript to the governed text pipeline (Agent 1 redacts again).
    return result.transcript, session


def run_full_pipeline(
    input_text: Optional[str] = None,
    runtime: Optional[APXVRuntime] = None,
    *,
    voice_session: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Run the complete APXV 3-agent pipeline.

    Args:
        input_text: Optional text to process. If None, uses a built-in
                    example containing PII for demonstration.

    Returns:
        The final attested_result dictionary.
    """
    if input_text is None:
        input_text = (
            "Contact John at john.doe@example.com or call (555) 123-4567. "
            "SSN: 123-45-6789. Card: 4111 1111 1111 1111."
        )

    print("=" * 60)
    print("APXV — Full Pipeline Execution")
    print("=" * 60)

    runtime = runtime or APXVRuntime()
    provider = runtime.provider

    # === Agent 1: Redaction ===
    print("\n[1/3] Running RuleGovernedRedactor (APXV-AGENT-001)...")
    redactor = RuleGovernedRedactor(runtime=runtime)
    redactor_output = redactor.process_text(input_text)
    print(f"      - Input hash: {redactor_output['input_hash'][:16]}...")
    print(f"      - Total redactions: {redactor_output['total_redactions']}")
    print(f"      - Rule hash: {redactor_output['rule_file_hash'][:16]}...")

    # === Agent 2: Workflow Orchestration ===
    print("\n[2/3] Running WorkflowOrchestrator (APXV-AGENT-002)...")
    orchestrator = WorkflowOrchestrator(runtime=runtime)
    workflow_output = orchestrator.execute_workflow(redactor_output=redactor_output)
    proposed = workflow_output["proposed_artifact"]
    print(f"      - Proposed artifact hash: {workflow_output['attestation_request']['artifact_hash'][:16]}...")
    print(f"      - Redactions in artifact: {proposed['output']['total_redactions']}")

    # === Agent 3: Attestation Coordination ===
    print("\n[3/3] Running AttestationCoordinator (APXV-AGENT-003)...")
    coordinator = AttestationCoordinator(runtime=runtime)
    final_output = coordinator.coordinate_attestation(workflow_output=workflow_output)
    attested = final_output["attested_result"]
    print(f"      - Governance decision: {attested['governance_decision']['decision']}")
    print(f"      - Full provenance hash: {attested['full_provenance_hash'][:16]}...")

    # === Persist final artifact ===
    print("\n[Write] Persisting attested result via SqliteArtifactProvider (local store)...")
    write_meta = provider.write_artifact(
        artifact=attested,
        name="attested_result_pipeline"
    )
    print(f"      - Written to: {write_meta['path']}")
    print(f"      - Artifact hash: {write_meta['hash'][:16]}...")

    if voice_session:
        attested["voice_session"] = voice_session
        provider.write_artifact(artifact=attested, name="attested_result_pipeline")

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE — Status: ATTESTED")
    print("=" * 60)

    return attested


def generate_zk_proof(
    attested_result: dict,
    base_path: Path,
    circuit: str = "redaction",
    redaction_proof: Optional[dict] = None,
) -> dict:
    """
    Call the Rust prover to produce a real, portable Groth16 proof.

    Supports all three circuits:
        - "redaction"
        - "rule-binding"
        - "pipeline"

    The output now contains real serialized proof_hex + vk_hex so that
    anyone can perform independent verification later without re-running
    the prover. This is the key upgrade for "real proofs".
    """
    import subprocess
    import tempfile

    from .prepare_proof_inputs import prepare_circuit_inputs

    circuit_inputs = prepare_circuit_inputs(
        attested_result,
        redaction_proof=redaction_proof,
    )

    # Map circuit name to the key in the prepared inputs
    input_key_map = {
        "redaction": "redaction_proof_inputs",
        "rule-binding": "rule_binding_inputs",
        "pipeline": "pipeline_attestation_inputs",
    }
    if circuit not in input_key_map:
        return {"status": "unsupported_circuit", "circuit": circuit}

    inputs_for_circuit = circuit_inputs[input_key_map[circuit]]

    with tempfile.TemporaryDirectory() as tmp:
        inputs_file = Path(tmp) / f"{circuit}_inputs.json"
        inputs_file.write_text(json.dumps(inputs_for_circuit, indent=2))

        from .rust_bins import build_apx_circuits_command

        print(f"\n[ZK] Invoking Rust Groth16 prover for circuit: {circuit}")
        print("     (First run will compile — can take 30-120s)")

        cmd, cwd = build_apx_circuits_command(
            base_path, "prove", circuit, "--inputs", str(inputs_file),
        )

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            print(result.stdout)
            if result.returncode != 0:
                print("Rust prover stderr:", result.stderr[-800:])
                return {"status": "proof_failed", "error": result.stderr[-500:]}

            # New output naming from the updated Rust binary
            proof_result_path = inputs_file.with_name(f"{circuit}_proof.json")
            if proof_result_path.exists():
                proof_data = json.loads(proof_result_path.read_text())
                from .zk_manifest import attach_key_metadata
                proof_data = attach_key_metadata(proof_data, circuit, base_path=base_path)
                verification_status = proof_data.get('verification_result', False)
                
                print(f"[ZK] Real portable Groth16 proof generated for {circuit}.")
                
                if verification_status is True:
                    print(f"     Immediate verification: VALID [OK]")
                else:
                    print(f"     Immediate verification: INVALID [FAIL] (Rust check failed)")
                
                print(f"     Proof is now independently verifiable via proof_hex + vk_hex.")
                return proof_data
            else:
                return {"status": "proof_output_missing"}

        except Exception as e:
            return {"status": "error_calling_rust", "error": str(e)}


def apply_e2ee_encryption(attested: dict, base_path: Path) -> dict:
    """Opt-in local E2EE: encrypt proposed_artifact and attach envelope."""
    from agents.encryption_engine import get_e2ee_instance

    e2ee = get_e2ee_instance(base_path=base_path)
    return e2ee.encrypt_artifact_payload(attested)


def _pop_flag_value(argv: list[str], flag: str) -> Optional[str]:
    if flag not in argv:
        return None
    idx = argv.index(flag)
    argv.pop(idx)
    if idx >= len(argv):
        raise SystemExit(f"Missing value for {flag}")
    return argv.pop(idx)


def main():
    """CLI entry point."""
    argv = list(sys.argv)
    with_proof = "--attest" in argv
    with_encrypt = "--encrypt" in argv
    voice_synthesize = "--voice-synthesize" in argv
    if voice_synthesize:
        argv.remove("--voice-synthesize")
    if with_proof:
        argv.remove("--attest")
    if with_encrypt:
        argv.remove("--encrypt")

    voice_file_raw = _pop_flag_value(argv, "--voice-file")
    voice_transcript = _pop_flag_value(argv, "--voice-transcript")
    voice_mode = _pop_flag_value(argv, "--voice-mode")

    input_parts = [arg for arg in argv[1:] if not arg.startswith("--")]
    input_text = " ".join(input_parts) if input_parts else None

    runtime = APXVRuntime()
    base = runtime.base_path

    voice_input, voice_session = prepare_voice_session(
        base_path=base,
        voice_file=Path(voice_file_raw) if voice_file_raw else None,
        voice_transcript=voice_transcript,
        voice_mode=voice_mode,
        synthesize_tts=voice_synthesize,
    )
    if voice_input is not None:
        input_text = voice_input

    attested = run_full_pipeline(
        input_text=input_text,
        runtime=runtime,
        voice_session=voice_session,
    )
    total_redactions = attested["proposed_artifact"]["output"]["total_redactions"]

    if with_proof:
        base = runtime.base_path
        provider = runtime.provider

        from .setup_zk import ensure_zk_setup

        print("\n[ZK] Ensuring trusted setup keys exist for all circuits...")
        ensure_zk_setup(base_path=base)

        # Generate proofs in dependency order: redaction â†’ rule-binding â†’ pipeline
        zk_result = generate_zk_proof(attested, base, circuit="redaction")
        attested["zk_proof_redaction"] = zk_result

        zk_rule = generate_zk_proof(
            attested, base, circuit="rule-binding", redaction_proof=zk_result
        )
        attested["zk_proof_rule_binding"] = zk_rule

        zk_pipeline = generate_zk_proof(
            attested, base, circuit="pipeline", redaction_proof=zk_result
        )
        attested["zk_proof_pipeline"] = zk_pipeline

        from agents.zk.bridge import generate_entity_proofs
        from agents.zk.bundle import build_dual_proof_bundle, build_governance_proof_bundle

        print("\n[Entity ZK] Generating entity Groth16 proofs (Track B)...")
        entity_bundle = generate_entity_proofs(attested, base_path=base)
        attested["entity_proofs"] = entity_bundle
        attested["governance_proofs"] = build_governance_proof_bundle(attested)
        attested["dual_proof_bundle"] = build_dual_proof_bundle(attested)

        entity_ok = all(
            proof.get("verification_result") is True
            for proof in entity_bundle.get("proofs", {}).values()
            if isinstance(proof, dict)
        )
        if entity_ok:
            extras = []
            if "batch_merkle" in entity_bundle.get("proofs", {}):
                extras.append("batch-merkle")
            inclusion_count = sum(
                1
                for key in entity_bundle.get("proofs", {})
                if key.startswith("merkle_inclusion_")
            )
            if inclusion_count:
                extras.append(f"merkle-inclusionÃ—{inclusion_count}")
            if "compliance" in entity_bundle.get("proofs", {}):
                extras.append("compliance")
            if "voice_redaction" in entity_bundle.get("proofs", {}):
                extras.append("voice-redaction")
            suffix = (" + " + " + ".join(extras)) if extras else ""
            print("      - Entity proofs: VALID (redaction-v1 + core-redaction" + suffix + ")")
        else:
            print("      - Entity proofs: one or more circuits failed — see artifact details")
            for name, proof in entity_bundle.get("proofs", {}).items():
                if not isinstance(proof, dict) or proof.get("verification_result") is True:
                    continue
                err = proof.get("error", proof.get("status", "unknown"))
                print(f"        Â· {name}: {str(err)[:300]}")

        # Re-persist the artifact with the real cryptographic proofs attached.
        # Use a name that still matches the "attested_result_pipeline_*.json" discovery pattern
        # used by verify_attestation.py --real-zk for better robustness.
        provider.write_artifact(artifact=attested, name="attested_result_pipeline_with_zk")
        runtime.system_audit.log_event(
            event_type="pipeline_attested_with_zk",
            data={"attestation_id": attested.get("attestation_id")},
        )

        print("\n[ZK] Attested result now includes dual proof bundles (governance + entity).")
        print("     Use verify_attestation.py --real-zk to perform independent verification.")

    if with_encrypt:
        base = runtime.base_path
        provider = runtime.provider

        print("\n[E2EE] Encrypting proposed artifact with local XSalsa20-Poly1305...")
        attested = apply_e2ee_encryption(attested, base)
        write_meta = provider.write_artifact(
            artifact=attested,
            name="attested_result_pipeline_encrypted",
        )
        runtime.system_audit.log_event(
            event_type="pipeline_attested_with_e2ee",
            data={
                "attestation_id": attested.get("attestation_id"),
                "artifact_path": write_meta.get("path"),
            },
        )
        print(f"      - Encrypted artifact written to: {write_meta['path']}")
        print(f"      - Public key: {attested['e2ee']['publicKey'][:16]}...")

    # Print compact final summary
    print("\nFinal Attestation Summary:")
    summary = {
        "attestation_id": attested["attestation_id"],
        "final_status": attested["final_status"],
        "governance_decision": attested["governance_decision"]["decision"],
        "total_redactions": total_redactions,
        "full_provenance_hash": attested["full_provenance_hash"][:32] + "...",
    }
    if attested.get("proposed_artifact", {}).get("status") == "E2EE_ENCRYPTED":
        summary["e2ee"] = True
    # Legacy key check retained for backward compatibility only
    if "zk_proof" in attested:
        summary["zk_verification"] = attested.get("zk_proof", {}).get("verification_result")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
