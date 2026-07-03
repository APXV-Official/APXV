// APX v1 — Rust Prover / Verifier Binary
// Copyright 2026 APXVdev
// Licensed under the Apache License, Version 2.0
//
// Minimal integration binary for Step 7.
// Provides prove and verify commands for the APX v1 circuits using ark-groth16.
//
// This is original work for the tiny APX v1 scope.
// It demonstrates end-to-end: Python agents → prepared inputs → real ZK proof → verification.

use std::env;
use std::fs;
use std::path::{Path, PathBuf};

use ark_bn254::{Bn254, Fr};
use ark_groth16::{Groth16, Proof, ProvingKey, VerifyingKey};
use ark_relations::r1cs::ConstraintSynthesizer;
use ark_serialize::{CanonicalDeserialize, CanonicalSerialize};
use ark_ff::PrimeField;
use ark_snark::SNARK;
use ark_std::Zero;

// Cryptographically secure RNG for ark-snark 0.4 (requires CryptoRng, not just Rng).
// We enable the 'getrandom' feature on ark-std so StdRng::from_entropy() works.
use ark_std::rand::rngs::StdRng;
use ark_std::rand::SeedableRng;

// We use #[path] so the original circuit files from Step 5 (in ../circuits/)
// can be used without moving them. All code remains original.
#[path = "../circuits/redaction_proof.rs"]
mod redaction_proof;

#[path = "../circuits/rule_binding.rs"]
mod rule_binding;

#[path = "../circuits/pipeline_attestation.rs"]
mod pipeline_attestation;

use redaction_proof::RedactionProofCircuit;
use rule_binding::RuleBindingCircuit;
use pipeline_attestation::PipelineAttestationCircuit;

/// Helper: Convert a hex string (SHA256 etc.) into a field element.
/// Takes the first 31 bytes to stay safely inside the field.
fn hex_to_fr(hex: &str) -> Fr {
    let clean = hex.trim_start_matches("0x");
    let bytes = hex::decode(clean).unwrap_or_else(|_| vec![0u8; 32]);
    let mut buf = [0u8; 32];
    let len = bytes.len().min(31);
    buf[32 - len..].copy_from_slice(&bytes[bytes.len() - len..]);
    Fr::from_be_bytes_mod_order(&buf)
}

fn load_json_inputs(path: &Path) -> serde_json::Value {
    let content = fs::read_to_string(path).expect("Failed to read inputs JSON");
    serde_json::from_str(&content).expect("Invalid JSON inputs")
}

/// Serialize a Groth16 proof to a hex string (compressed form).
fn serialize_proof(proof: &Proof<Bn254>) -> String {
    let mut bytes = Vec::new();
    proof.serialize_compressed(&mut bytes).expect("Failed to serialize proof");
    hex::encode(bytes)
}

/// Serialize a verifying key to a hex string (compressed form).
fn serialize_vk(vk: &VerifyingKey<Bn254>) -> String {
    let mut bytes = Vec::new();
    vk.serialize_compressed(&mut bytes).expect("Failed to serialize vk");
    hex::encode(bytes)
}

/// Deserialize a proof from hex.
fn deserialize_proof(hex_str: &str) -> Proof<Bn254> {
    let bytes = hex::decode(hex_str.trim_start_matches("0x")).expect("Bad proof hex");
    Proof::<Bn254>::deserialize_compressed(&mut &bytes[..]).expect("Failed to deserialize proof")
}

/// Deserialize a verifying key from hex.
fn deserialize_vk(hex_str: &str) -> VerifyingKey<Bn254> {
    let bytes = hex::decode(hex_str.trim_start_matches("0x")).expect("Bad vk hex");
    VerifyingKey::<Bn254>::deserialize_compressed(&mut &bytes[..]).expect("Failed to deserialize vk")
}

/// --- Honest Trusted Setup Helpers (arkworks 0.4 native) ---
/// These implement the correct approach per Phase 1 honest-setup requirements:
/// Perform setup ONCE with strong entropy, serialize the keys, and load them
/// for every subsequent proof. This eliminates per-proof toxic waste and
/// provides a stable, versionable verification key.

fn save_proving_key(pk: &ark_groth16::ProvingKey<Bn254>, path: &Path) {
    let mut bytes = Vec::new();
    pk.serialize_compressed(&mut bytes).expect("Failed to serialize proving key");
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).expect("Failed to create keys directory");
    }
    fs::write(path, bytes).expect("Failed to write proving key");
}

fn load_proving_key(path: &Path) -> ark_groth16::ProvingKey<Bn254> {
    let bytes = fs::read(path).expect("Failed to read proving key");
    ark_groth16::ProvingKey::<Bn254>::deserialize_compressed(&mut &bytes[..])
        .expect("Failed to deserialize proving key")
}

fn save_verifying_key(vk: &VerifyingKey<Bn254>, path: &Path) {
    let mut bytes = Vec::new();
    vk.serialize_compressed(&mut bytes).expect("Failed to serialize verifying key");
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).expect("Failed to create keys directory");
    }
    fs::write(path, bytes).expect("Failed to write verifying key");
}

fn load_verifying_key(path: &Path) -> VerifyingKey<Bn254> {
    let bytes = fs::read(path).expect("Failed to read verifying key");
    VerifyingKey::<Bn254>::deserialize_compressed(&mut &bytes[..])
        .expect("Failed to deserialize verifying key")
}

/// Returns the filesystem paths for the persisted proving and verifying keys
/// for a given circuit. Keys live under rust/keys/ (created on first setup).
fn get_key_paths(circuit_name: &str) -> (PathBuf, PathBuf) {
    let base = Path::new("keys").join(circuit_name);
    let pk_path = base.with_extension("pk");
    let vk_path = base.with_extension("vk");
    (pk_path, vk_path)
}

/// Performs a one-time honest trusted setup for the named circuit and persists
/// the resulting ProvingKey + VerifyingKey to disk (compressed ark-serialize format).
///
/// This is the arkworks 0.4 correct pattern for a single-party (honest) setup:
/// - Run once per circuit (or after circuit change).
/// - The resulting keys are then used for all subsequent proofs of that circuit.
/// - The "toxic waste" (the rng used during setup) is discarded after this run.
///
/// Per Phase 1 criteria #1 and #4 (honest setup, portable proofs).
fn run_one_time_setup(circuit_name: &str) {
    let mut rng = StdRng::from_entropy();

    let (pk_path, vk_path) = get_key_paths(circuit_name);

    println!("APX — Running one-time honest setup for circuit: {}", circuit_name);
    println!("(This uses circuit_specific_setup + ark-serialize. Single-party for Phase 1.)");

    match circuit_name {
        "redaction" => {
            let circuit = RedactionProofCircuit {
                original_hash: Fr::zero(),
                redacted_hash: Fr::zero(),
                redaction_count: Fr::zero(),
            };
            let (pk, vk) = Groth16::<Bn254>::circuit_specific_setup(circuit, &mut rng)
                .expect("Setup failed for redaction");
            save_proving_key(&pk, &pk_path);
            save_verifying_key(&vk, &vk_path);
        }
        "rule-binding" => {
            let circuit = RuleBindingCircuit {
                rule_hash: Fr::zero(),
                redaction_proof_hash: Fr::zero(),
                redaction_count: Fr::zero(),
            };
            let (pk, vk) = Groth16::<Bn254>::circuit_specific_setup(circuit, &mut rng)
                .expect("Setup failed for rule-binding");
            save_proving_key(&pk, &pk_path);
            save_verifying_key(&vk, &vk_path);
        }
        "pipeline" => {
            let circuit = PipelineAttestationCircuit {
                rule_hash: Fr::zero(),
                workflow_hash: Fr::zero(),
                knowledge_hash: Fr::zero(),
                final_governance_decision: Fr::zero(),
                agent_chain_hash: Fr::zero(),
            };
            let (pk, vk) = Groth16::<Bn254>::circuit_specific_setup(circuit, &mut rng)
                .expect("Setup failed for pipeline");
            save_proving_key(&pk, &pk_path);
            save_verifying_key(&vk, &vk_path);
        }
        other => {
            eprintln!("Unknown circuit for setup: {}. Use redaction | rule-binding | pipeline", other);
            std::process::exit(1);
        }
    }

    println!("Setup complete. Keys written to:");
    println!("  Proving key:  {}", pk_path.display());
    println!("  Verifying key: {}", vk_path.display());
    println!("You can now run: cargo run -- prove {} --inputs <file>", circuit_name);
}

/// Proving path that uses already-loaded persisted keys (the correct production pattern).
/// Returns (proof, immediate_verification_result).
fn prove_with_loaded_keys<C: ConstraintSynthesizer<Fr>>(
    circuit: C,
    public_inputs: Vec<Fr>,
    pk: &ProvingKey<Bn254>,
    vk: &VerifyingKey<Bn254>,
) -> (Proof<Bn254>, bool) {
    let mut rng = StdRng::from_entropy();

    let proof = Groth16::<Bn254>::prove(pk, circuit, &mut rng)
        .expect("Proving failed");

    // For Phase 1 test stability, we report the result of the internal check
    // but the authoritative verification is done via the standalone `verify` command
    // using the persisted VK. The internal check here is a convenience only.
    let valid = Groth16::<Bn254>::verify(vk, &public_inputs, &proof)
        .unwrap_or(false);

    (proof, valid)
}

/// Legacy proving function (still present for reference / minimal diff).
/// Now only used by the setup routine. All normal "prove" operations should go
/// through prove_with_loaded_keys after running `setup`.
fn prove_circuit<C: ConstraintSynthesizer<Fr> + Clone>(
    circuit: C,
    public_inputs: Vec<Fr>,
) -> (Proof<Bn254>, VerifyingKey<Bn254>, bool) {
    let mut rng = StdRng::from_entropy();

    // NOTE (Phase 1 honest-setup requirements):
    // circuit_specific_setup is only acceptable inside the explicit one-time `setup` command.
    // Normal prove paths must load persisted keys. This function is intentionally left
    // only for the setup helper and should not be called from the "prove" CLI arm.
    let (pk, vk) = Groth16::<Bn254>::circuit_specific_setup(circuit.clone(), &mut rng)
        .expect("Setup failed");

    let proof = Groth16::<Bn254>::prove(&pk, circuit, &mut rng)
        .expect("Proving failed");

    let valid = Groth16::<Bn254>::verify(&vk, &public_inputs, &proof)
        .unwrap_or(false);

    (proof, vk, valid)
}

/// Independent verification from serialized artifacts.
/// This is the key function that makes proofs "real" — anyone with the proof bytes,
/// vk bytes, and public inputs can verify without re-running the prover.
fn verify_serialized(
    proof_hex: &str,
    vk_hex: &str,
    public_inputs: Vec<Fr>,
) -> bool {
    let proof = deserialize_proof(proof_hex);
    let vk = deserialize_vk(vk_hex);

    Groth16::<Bn254>::verify(&vk, &public_inputs, &proof).unwrap_or(false)
}

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        eprintln!("APX Rust Prover/Verifier (with real portable Groth16 proofs)");
        eprintln!("Usage:");
        eprintln!("  apx-circuits setup <redaction|rule-binding|pipeline>");
        eprintln!("  apx-circuits prove <circuit> --inputs <inputs.json> [--out <proof.json>]");
        eprintln!("  apx-circuits verify <circuit> --proof <proof_bundle.json>");
        eprintln!("      (proof bundle must contain proof_hex, vk_hex, and public_inputs)");
        eprintln!("");
        eprintln!("First run 'setup' once per circuit (honest one-time setup + persisted keys).");
        eprintln!("Circuits: redaction | rule-binding | pipeline");
        std::process::exit(1);
    }

    let command = &args[1];

    match command.as_str() {
        "setup" => {
            if args.len() < 3 {
                eprintln!("Usage: apx-circuits setup <redaction|rule-binding|pipeline>");
                std::process::exit(1);
            }
            let circuit_name = &args[2];
            run_one_time_setup(circuit_name);
        }

        "prove" => {
            if args.len() < 5 || args[3] != "--inputs" {
                eprintln!("Usage: apx-circuits prove <redaction|rule-binding|pipeline> --inputs <file>");
                std::process::exit(1);
            }

            let circuit_name = &args[2];
            let inputs_path = Path::new(&args[4]);
            let inputs = load_json_inputs(inputs_path);

            println!("APX — Proving circuit: {} with real Groth16 (BN254)...", circuit_name);

            // Load persisted keys from one-time honest setup (Criterion #1 & #4)
            let (pk_path, vk_path) = get_key_paths(circuit_name);
            if !pk_path.exists() || !vk_path.exists() {
                eprintln!("ERROR: No trusted setup keys found for circuit '{}'.", circuit_name);
                eprintln!("Run first:  cargo run -- setup {}", circuit_name);
                eprintln!("This is required for honest setup (Phase 1 trusted setup).");
                std::process::exit(1);
            }

            let pk = load_proving_key(&pk_path);
            let vk = load_verifying_key(&vk_path);

            let (proof, valid, public_inputs_json) = match circuit_name.as_str() {
                "redaction" => {
                    let original = hex_to_fr(inputs["original_hash"].as_str().unwrap());
                    let redacted = hex_to_fr(inputs["redacted_hash"].as_str().unwrap());
                    let count = Fr::from(inputs["redaction_count"].as_u64().unwrap_or(0));

                    let circuit = RedactionProofCircuit {
                        original_hash: original,
                        redacted_hash: redacted,
                        redaction_count: count,
                    };
                    let public_inputs = vec![original, redacted, count];
                    let (proof, valid) = prove_with_loaded_keys(circuit, public_inputs.clone(), &pk, &vk);

                    let pi_json = serde_json::json!({
                        "original_hash": inputs["original_hash"],
                        "redacted_hash": inputs["redacted_hash"],
                        "redaction_count": inputs["redaction_count"],
                    });
                    (proof, valid, pi_json)
                }

                "rule-binding" => {
                    let rule = hex_to_fr(inputs["rule_hash"].as_str().unwrap());
                    let proof_hash = hex_to_fr(inputs["redaction_proof_hash"].as_str().unwrap());
                    let count = Fr::from(inputs["redaction_count"].as_u64().unwrap_or(0));

                    let circuit = RuleBindingCircuit {
                        rule_hash: rule,
                        redaction_proof_hash: proof_hash,
                        redaction_count: count,
                    };
                    let public_inputs = vec![rule, proof_hash, count];
                    let (proof, valid) = prove_with_loaded_keys(circuit, public_inputs.clone(), &pk, &vk);

                    let pi_json = serde_json::json!({
                        "rule_hash": inputs["rule_hash"],
                        "redaction_proof_hash": inputs["redaction_proof_hash"],
                        "redaction_count": inputs["redaction_count"],
                    });
                    (proof, valid, pi_json)
                }

                "pipeline" => {
                    let rule = hex_to_fr(inputs["rule_hash"].as_str().unwrap());
                    let wf = hex_to_fr(inputs["workflow_hash"].as_str().unwrap());
                    let kb = hex_to_fr(inputs["knowledge_hash"].as_str().unwrap());
                    let gov = hex_to_fr(inputs["final_governance_decision"].as_str().unwrap());
                    let chain = hex_to_fr(inputs["agent_chain_hash"].as_str().unwrap());

                    let circuit = PipelineAttestationCircuit {
                        rule_hash: rule,
                        workflow_hash: wf,
                        knowledge_hash: kb,
                        final_governance_decision: gov,
                        agent_chain_hash: chain,
                    };
                    let public_inputs = vec![rule, wf, kb, gov, chain];
                    let (proof, valid) = prove_with_loaded_keys(circuit, public_inputs.clone(), &pk, &vk);

                    let pi_json = serde_json::json!({
                        "rule_hash": inputs["rule_hash"],
                        "workflow_hash": inputs["workflow_hash"],
                        "knowledge_hash": inputs["knowledge_hash"],
                        "final_governance_decision": inputs["final_governance_decision"],
                        "agent_chain_hash": inputs["agent_chain_hash"],
                    });
                    (proof, valid, pi_json)
                }

                other => {
                    eprintln!("Unknown circuit: {}. Use redaction | rule-binding | pipeline", other);
                    std::process::exit(1);
                }
            };

            // Serialize for independent verification later.
            // We already have the vk from the loaded persisted keys (no toxic waste per proof).
            let proof_hex = serialize_proof(&proof);
            let vk_hex = serialize_vk(&vk);

            let result = serde_json::json!({
                "circuit": circuit_name,
                "status": if valid { "VERIFIED" } else { "INVALID" },
                "proof_generated": true,
                "verification_result": valid,
                "public_inputs": public_inputs_json,
                "proof_hex": proof_hex,
                "vk_hex": vk_hex,
                "note": "Real Groth16 proof over BN254. Proof and VK are serialized (compressed). Use the 'verify' command with these values for independent verification."
            });

            // Determine output path
            let out_path = if args.len() >= 7 && args[5] == "--out" {
                Path::new(&args[6]).to_path_buf()
            } else {
                inputs_path.with_file_name(format!("{}_proof.json", circuit_name))
            };

            fs::write(&out_path, serde_json::to_string_pretty(&result).unwrap())
                .expect("Failed to write proof bundle");

            println!("Proof bundle written to: {}", out_path.display());
            println!(
                "Immediate verification result: {}",
                if valid { "VALID [OK]" } else { "INVALID [FAIL]" }
            );
            println!("Proof and VK are now portable and independently verifiable.");
        }

        "verify" => {
            // Portable third-party verification using only the proof bundle.
            // The bundle must contain proof_hex, vk_hex, and public_inputs.
            if args.len() < 5 || args[3] != "--proof" {
                eprintln!("Usage: apx-circuits verify <redaction|rule-binding|pipeline> --proof <proof_bundle.json>");
                std::process::exit(1);
            }

            let circuit_name = &args[2];
            let proof_path = Path::new(&args[4]);

            let proof_bundle: serde_json::Value = serde_json::from_str(
                &fs::read_to_string(proof_path).expect("Failed to read proof bundle")
            ).expect("Invalid proof JSON");

            let proof_hex = proof_bundle["proof_hex"]
                .as_str()
                .expect("proof_hex field missing in proof bundle");
            let vk_hex = proof_bundle["vk_hex"]
                .as_str()
                .expect("vk_hex field missing in proof bundle");
            let inputs = &proof_bundle["public_inputs"];

            let public_inputs: Vec<Fr> = match circuit_name.as_str() {
                "redaction" => {
                    vec![
                        hex_to_fr(inputs["original_hash"].as_str().expect("original_hash missing")),
                        hex_to_fr(inputs["redacted_hash"].as_str().expect("redacted_hash missing")),
                        Fr::from(inputs["redaction_count"].as_u64().unwrap_or(0)),
                    ]
                }
                "rule-binding" => {
                    vec![
                        hex_to_fr(inputs["rule_hash"].as_str().expect("rule_hash missing")),
                        hex_to_fr(
                            inputs["redaction_proof_hash"]
                                .as_str()
                                .expect("redaction_proof_hash missing"),
                        ),
                        Fr::from(inputs["redaction_count"].as_u64().unwrap_or(0)),
                    ]
                }
                "pipeline" => {
                    let governance = inputs["final_governance_decision"].as_str().expect(
                        "final_governance_decision must be a hex string",
                    );
                    vec![
                        hex_to_fr(inputs["rule_hash"].as_str().expect("rule_hash missing")),
                        hex_to_fr(inputs["workflow_hash"].as_str().expect("workflow_hash missing")),
                        hex_to_fr(inputs["knowledge_hash"].as_str().expect("knowledge_hash missing")),
                        hex_to_fr(governance),
                        hex_to_fr(inputs["agent_chain_hash"].as_str().expect("agent_chain_hash missing")),
                    ]
                }
                other => {
                    eprintln!("Unknown circuit: {}", other);
                    std::process::exit(1);
                }
            };

            let valid = verify_serialized(proof_hex, vk_hex, public_inputs);

            println!("APX — Independent Groth16 verification (portable mode)");
            println!("Circuit: {}", circuit_name);
            println!("Result: {}", if valid { "VALID [OK]" } else { "INVALID [FAIL]" });
            println!("Verification used serialized proof_hex + vk_hex (no re-proving).");

            if !valid {
                std::process::exit(1);
            }
        }

        _ => {
            eprintln!("Unknown command: {}", command);
            std::process::exit(1);
        }
    }
}
