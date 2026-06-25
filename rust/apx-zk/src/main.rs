// Copyright 2026 APXV Official
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

//! APX-ZK CLI: Groth16 setup, prove, and verify for entity circuits.

use std::env;
use std::fs;
use std::path::{Path, PathBuf};

use ark_bn254::{Bn254, Fr};
use ark_ff::PrimeField;
use ark_groth16::{Groth16, Proof};
use ark_serialize::{CanonicalDeserialize, CanonicalSerialize};
use ark_snark::SNARK;
use ark_std::rand::rngs::StdRng;
use ark_std::rand::SeedableRng;
use serde_json::Value;

use apx_zk::circuits::{
    batch_merkle::BatchMerkleCircuit,
    compliance::ComplianceCircuit,
    core_redaction::CoreRedactionCircuit,
    merkle_inclusion::MerkleInclusionCircuit,
    normalization::NormalizationCircuit,
    redaction_v1::RedactionProofV1Circuit,
    threat::ThreatCircuit,
    voice_redaction::VoiceRedactionCircuit,
};
use apx_zk::keygen::{load_proving_key, load_verification_key};
use apx_zk::poseidon::Poseidon;

const CIRCUITS: &[&str] = &[
    "normalization",
    "core-redaction",
    "compliance",
    "threat",
    "voice-redaction",
    "redaction-v1",
    "merkle-inclusion",
    "batch-merkle",
];

fn usage() -> ! {
    eprintln!("APX-ZK — Entity Groth16 Prover/Verifier (BN254)");
    eprintln!();
    eprintln!("Usage:");
    eprintln!("  apx-zk setup <circuit>");
    eprintln!("  apx-zk prove <circuit> --inputs <inputs.json> [--out <proof.json>]");
    eprintln!("  apx-zk verify <circuit> --inputs <inputs.json>");
    eprintln!("  apx-zk hash-two <left_decimal> <right_decimal>");
    eprintln!("  apx-zk hash-fields <decimal> [<decimal> ...]");
    eprintln!();
    eprintln!("Circuits:");
    for c in CIRCUITS {
        eprintln!("  {}", c);
    }
    std::process::exit(1);
}

fn validate_circuit(name: &str) -> &str {
    if CIRCUITS.contains(&name) {
        name
    } else {
        eprintln!("Unknown circuit: {}", name);
        usage();
    }
}

fn key_paths(circuit: &str) -> (PathBuf, PathBuf) {
    let base = Path::new("keys").join(circuit);
    (base.with_extension("pk"), base.with_extension("vk"))
}

fn load_json(path: &Path) -> Value {
    let content = fs::read_to_string(path).unwrap_or_else(|e| {
        eprintln!("Failed to read {}: {}", path.display(), e);
        std::process::exit(1);
    });
    serde_json::from_str(&content).unwrap_or_else(|e| {
        eprintln!("Invalid JSON in {}: {}", path.display(), e);
        std::process::exit(1);
    })
}

fn json_fr(v: &Value, key: &str) -> Fr {
    if let Some(n) = v.get(key).and_then(|x| x.as_u64()) {
        return Fr::from(n);
    }
    if let Some(s) = v.get(key).and_then(|x| x.as_str()) {
        let trimmed = s.trim();
        let hex_body = trimmed
            .trim_start_matches("0x")
            .trim_start_matches("0X");
        let looks_like_byte_hex = trimmed.starts_with("0x")
            || trimmed.starts_with("0X")
            || hex_body.chars().any(|c| matches!(c, 'a'..='f' | 'A'..='F'));
        // Bare decimal field elements use only 0-9 but are still valid hex; decode those
        // as decimal strings. SHA-style hashes include a-f and stay on the byte path.
        if looks_like_byte_hex {
            if let Ok(bytes) = hex::decode(hex_body) {
                let mut buf = [0u8; 32];
                let len = bytes.len().min(32);
                buf[32 - len..].copy_from_slice(&bytes[bytes.len() - len..]);
                return Fr::from_be_bytes_mod_order(&buf);
            }
        }
        if let Ok(f) = Fr::from_str(s) {
            return f;
        }
    }
    eprintln!("Missing or invalid field element: {}", key);
    std::process::exit(1);
}

fn json_fr_array<const N: usize>(v: &Value, key: &str) -> [Fr; N] {
    let arr = v.get(key).and_then(|x| x.as_array()).unwrap_or_else(|| {
        eprintln!("Missing or invalid array field: {}", key);
        std::process::exit(1);
    });
    if arr.len() != N {
        eprintln!("Array {} must have {} elements, got {}", key, N, arr.len());
        std::process::exit(1);
    }
    let mut out = [Fr::from(0u64); N];
    for (i, item) in arr.iter().enumerate() {
        if let Some(n) = item.as_u64() {
            out[i] = Fr::from(n);
        } else if let Some(s) = item.as_str() {
            out[i] = Fr::from_str(s).unwrap_or_else(|_| {
                eprintln!("Invalid field element in {}[{}]", key, i);
                std::process::exit(1);
            });
        } else {
            eprintln!("Invalid element in {}[{}]", key, i);
            std::process::exit(1);
        }
    }
    out
}

fn json_fr_matrix<const R: usize, const C: usize>(v: &Value, key: &str) -> [[Fr; C]; R] {
    let rows = v.get(key).and_then(|x| x.as_array()).unwrap_or_else(|| {
        eprintln!("Missing or invalid matrix field: {}", key);
        std::process::exit(1);
    });
    if rows.len() != R {
        eprintln!("Matrix {} must have {} rows, got {}", key, R, rows.len());
        std::process::exit(1);
    }
    let mut out = [[Fr::from(0u64); C]; R];
    for (r, row) in rows.iter().enumerate() {
        let cols = row.as_array().unwrap_or_else(|| {
            eprintln!("Row {} of {} is not an array", r, key);
            std::process::exit(1);
        });
        if cols.len() != C {
            eprintln!("Row {} of {} must have {} columns", r, key, C);
            std::process::exit(1);
        }
        for (c, item) in cols.iter().enumerate() {
            out[r][c] = if let Some(n) = item.as_u64() {
                Fr::from(n)
            } else if let Some(s) = item.as_str() {
                Fr::from_str(s).unwrap_or_else(|_| {
                    eprintln!("Invalid field element in {}[{}][{}]", key, r, c);
                    std::process::exit(1);
                })
            } else {
                eprintln!("Invalid element in {}[{}][{}]", key, r, c);
                std::process::exit(1);
            };
        }
    }
    out
}

use std::str::FromStr;

enum BuiltCircuit {
    Normalization(NormalizationCircuit, Vec<Fr>),
    CoreRedaction(CoreRedactionCircuit, Vec<Fr>),
    Compliance(ComplianceCircuit, Vec<Fr>),
    Threat(ThreatCircuit, Vec<Fr>),
    VoiceRedaction(VoiceRedactionCircuit, Vec<Fr>),
    RedactionV1(RedactionProofV1Circuit, Vec<Fr>),
    MerkleInclusion(MerkleInclusionCircuit, Vec<Fr>),
    BatchMerkle(BatchMerkleCircuit, Vec<Fr>),
}

impl BuiltCircuit {
    fn prove(self, pk: &ark_groth16::ProvingKey<Bn254>, vk: &ark_groth16::VerifyingKey<Bn254>) -> (Proof<Bn254>, bool) {
        let mut rng = StdRng::from_entropy();
        match self {
            BuiltCircuit::Normalization(c, pi) => {
                let proof = Groth16::<Bn254>::prove(pk, c, &mut rng).expect("prove failed");
                let valid = Groth16::<Bn254>::verify(vk, &pi, &proof).unwrap_or(false);
                (proof, valid)
            }
            BuiltCircuit::CoreRedaction(c, pi) => {
                let proof = Groth16::<Bn254>::prove(pk, c, &mut rng).expect("prove failed");
                let valid = Groth16::<Bn254>::verify(vk, &pi, &proof).unwrap_or(false);
                (proof, valid)
            }
            BuiltCircuit::Compliance(c, pi) => {
                let proof = Groth16::<Bn254>::prove(pk, c, &mut rng).expect("prove failed");
                let valid = Groth16::<Bn254>::verify(vk, &pi, &proof).unwrap_or(false);
                (proof, valid)
            }
            BuiltCircuit::Threat(c, pi) => {
                let proof = Groth16::<Bn254>::prove(pk, c, &mut rng).expect("prove failed");
                let valid = Groth16::<Bn254>::verify(vk, &pi, &proof).unwrap_or(false);
                (proof, valid)
            }
            BuiltCircuit::VoiceRedaction(c, pi) => {
                let proof = Groth16::<Bn254>::prove(pk, c, &mut rng).expect("prove failed");
                let valid = Groth16::<Bn254>::verify(vk, &pi, &proof).unwrap_or(false);
                (proof, valid)
            }
            BuiltCircuit::RedactionV1(c, pi) => {
                let proof = Groth16::<Bn254>::prove(pk, c, &mut rng).expect("prove failed");
                let valid = Groth16::<Bn254>::verify(vk, &pi, &proof).unwrap_or(false);
                (proof, valid)
            }
            BuiltCircuit::MerkleInclusion(c, pi) => {
                let proof = Groth16::<Bn254>::prove(pk, c, &mut rng).expect("prove failed");
                let valid = Groth16::<Bn254>::verify(vk, &pi, &proof).unwrap_or(false);
                (proof, valid)
            }
            BuiltCircuit::BatchMerkle(c, pi) => {
                let proof = Groth16::<Bn254>::prove(pk, c, &mut rng).expect("prove failed");
                let valid = Groth16::<Bn254>::verify(vk, &pi, &proof).unwrap_or(false);
                (proof, valid)
            }
        }
    }

    fn public_inputs(&self) -> Vec<Fr> {
        match self {
            BuiltCircuit::Normalization(_, pi) => pi.clone(),
            BuiltCircuit::CoreRedaction(_, pi) => pi.clone(),
            BuiltCircuit::Compliance(_, pi) => pi.clone(),
            BuiltCircuit::Threat(_, pi) => pi.clone(),
            BuiltCircuit::VoiceRedaction(_, pi) => pi.clone(),
            BuiltCircuit::RedactionV1(_, pi) => pi.clone(),
            BuiltCircuit::MerkleInclusion(_, pi) => pi.clone(),
            BuiltCircuit::BatchMerkle(_, pi) => pi.clone(),
        }
    }
}

fn build_circuit(name: &str, v: &Value) -> BuiltCircuit {
    match name {
        "normalization" => {
            let original_hash = json_fr(v, "original_hash");
            let normalized_hash = json_fr(v, "normalized_hash");
            let feature_bitmap = json_fr(v, "feature_bitmap");
            let entropy_drop = json_fr(v, "entropy_drop");
            let circuit = NormalizationCircuit {
                original_hash,
                normalized_hash,
                feature_bitmap,
                entropy_drop,
                original_length: json_fr(v, "original_length"),
                normalized_length: json_fr(v, "normalized_length"),
                feature_count: json_fr(v, "feature_count"),
            };
            let pi = vec![original_hash, normalized_hash, feature_bitmap, entropy_drop];
            BuiltCircuit::Normalization(circuit, pi)
        }
        "core-redaction" => {
            let merkle_root = json_fr(v, "merkle_root");
            let entity_count = json_fr(v, "entity_count");
            let circuit = CoreRedactionCircuit {
                merkle_root,
                entity_count,
                original_data_hash: json_fr(v, "original_data_hash"),
                redacted_data_hash: json_fr(v, "redacted_data_hash"),
            };
            let pi = vec![merkle_root, entity_count];
            BuiltCircuit::CoreRedaction(circuit, pi)
        }
        "compliance" => {
            let entity_count = json_fr(v, "entity_count");
            let policy_id = json_fr(v, "policy_id");
            let circuit = ComplianceCircuit {
                entity_count,
                policy_id,
                original_hash: json_fr(v, "original_hash"),
                redacted_hash: json_fr(v, "redacted_hash"),
            };
            let pi = vec![entity_count, policy_id];
            BuiltCircuit::Compliance(circuit, pi)
        }
        "threat" => {
            let threat_score = json_fr(v, "threat_score");
            let policy_id = json_fr(v, "policy_id");
            let circuit = ThreatCircuit {
                threat_score,
                policy_id,
                original_hash: json_fr(v, "original_hash"),
                mitigated_hash: json_fr(v, "mitigated_hash"),
            };
            let pi = vec![threat_score, policy_id];
            BuiltCircuit::Threat(circuit, pi)
        }
        "voice-redaction" => {
            let entity_count = json_fr(v, "entity_count");
            let policy_id = json_fr(v, "policy_id");
            let circuit = VoiceRedactionCircuit {
                entity_count,
                policy_id,
                original_hash: json_fr(v, "original_hash"),
                redacted_hash: json_fr(v, "redacted_hash"),
            };
            let pi = vec![entity_count, policy_id];
            BuiltCircuit::VoiceRedaction(circuit, pi)
        }
        "redaction-v1" => {
            let merkle_root = json_fr(v, "merkle_root");
            let entity_count = json_fr(v, "entity_count");
            let entities_digest = json_fr(v, "entities_digest");
            let original_data_hash = json_fr(v, "original_data_hash");
            let redacted_data_hash = json_fr(v, "redacted_data_hash");
            let leaf_commitments = json_fr_array::<8>(v, "leaf_commitments");
            let circuit = RedactionProofV1Circuit {
                merkle_root,
                entity_count,
                entities_digest,
                original_data_hash,
                redacted_data_hash,
                leaf_commitments,
            };
            let pi = vec![
                merkle_root,
                entity_count,
                entities_digest,
                original_data_hash,
                redacted_data_hash,
            ];
            BuiltCircuit::RedactionV1(circuit, pi)
        }
        "merkle-inclusion" => {
            let merkle_root = json_fr(v, "merkle_root");
            let circuit = MerkleInclusionCircuit {
                merkle_root,
                leaf: json_fr(v, "leaf"),
                path_elements: json_fr_array::<8>(v, "path_elements"),
                path_indices: json_fr_array::<8>(v, "path_indices"),
            };
            let pi = vec![merkle_root];
            BuiltCircuit::MerkleInclusion(circuit, pi)
        }
        "batch-merkle" => {
            let merkle_root = json_fr(v, "merkle_root");
            let entity_count = json_fr(v, "entity_count");
            let circuit = BatchMerkleCircuit {
                merkle_root,
                entity_count,
                leaves: json_fr_array::<4>(v, "leaves"),
                path_elements: json_fr_matrix::<4, 8>(v, "path_elements"),
                path_indices: json_fr_matrix::<4, 8>(v, "path_indices"),
            };
            let pi = vec![merkle_root, entity_count];
            BuiltCircuit::BatchMerkle(circuit, pi)
        }
        _ => unreachable!(),
    }
}

fn run_setup(circuit: &str) {
    let (pk_path, vk_path) = key_paths(circuit);
    if let Some(parent) = pk_path.parent() {
        fs::create_dir_all(parent).expect("create keys dir");
    }

    println!("APX-ZK — Running Groth16 setup for: {}", circuit);
    let mut rng = StdRng::from_entropy();

    let (pk, vk) = match circuit {
        "normalization" => Groth16::<Bn254>::circuit_specific_setup(
            NormalizationCircuit {
                original_hash: Fr::from(1u64),
                normalized_hash: Fr::from(2u64),
                feature_bitmap: Fr::from(127u64),
                entropy_drop: Fr::from(50u64),
                original_length: Fr::from(1000u64),
                normalized_length: Fr::from(900u64),
                feature_count: Fr::from(5u64),
            },
            &mut rng,
        ),
        "core-redaction" => Groth16::<Bn254>::circuit_specific_setup(
            CoreRedactionCircuit {
                merkle_root: Fr::from(12345u64),
                entity_count: Fr::from(10u64),
                original_data_hash: Fr::from(111111u64),
                redacted_data_hash: Fr::from(222222u64),
            },
            &mut rng,
        ),
        "compliance" => Groth16::<Bn254>::circuit_specific_setup(
            ComplianceCircuit {
                entity_count: Fr::from(5u64),
                policy_id: Fr::from(3u64),
                original_hash: Fr::from(111111u64),
                redacted_hash: Fr::from(222222u64),
            },
            &mut rng,
        ),
        "threat" => Groth16::<Bn254>::circuit_specific_setup(
            ThreatCircuit {
                threat_score: Fr::from(80u64),
                policy_id: Fr::from(2u64),
                original_hash: Fr::from(111111u64),
                mitigated_hash: Fr::from(222222u64),
            },
            &mut rng,
        ),
        "voice-redaction" => Groth16::<Bn254>::circuit_specific_setup(
            VoiceRedactionCircuit {
                entity_count: Fr::from(3u64),
                policy_id: Fr::from(3u64),
                original_hash: Fr::from(111111u64),
                redacted_hash: Fr::from(222222u64),
            },
            &mut rng,
        ),
        "redaction-v1" => {
            let leaf_commitments = [
                Fr::from(1000u64),
                Fr::from(2000u64),
                Fr::from(3000u64),
                Fr::from(4000u64),
                Fr::from(5000u64),
                Fr::from(6000u64),
                Fr::from(7000u64),
                Fr::from(8000u64),
            ];
            let digest = Poseidon::new().hash(&leaf_commitments.to_vec());
            Groth16::<Bn254>::circuit_specific_setup(
                RedactionProofV1Circuit {
                    merkle_root: Fr::from(99999u64),
                    entity_count: Fr::from(8u64),
                    entities_digest: digest,
                    original_data_hash: Fr::from(111111u64),
                    redacted_data_hash: Fr::from(222222u64),
                    leaf_commitments,
                },
                &mut rng,
            )
        }
        "merkle-inclusion" => Groth16::<Bn254>::circuit_specific_setup(
            MerkleInclusionCircuit {
                merkle_root: Fr::from(12345u64),
                leaf: Fr::from(1000u64),
                path_elements: [Fr::from(2000u64); 8],
                path_indices: [Fr::from(0u64); 8],
            },
            &mut rng,
        ),
        "batch-merkle" => Groth16::<Bn254>::circuit_specific_setup(
            BatchMerkleCircuit {
                merkle_root: Fr::from(12345u64),
                entity_count: Fr::from(4u64),
                leaves: [Fr::from(1000u64); 4],
                path_elements: [[Fr::from(0u64); 8]; 4],
                path_indices: [[Fr::from(0u64); 8]; 4],
            },
            &mut rng,
        ),
        _ => unreachable!(),
    }
    .unwrap_or_else(|e| {
        eprintln!("Setup failed: {}", e);
        std::process::exit(1);
    });

    let mut pk_bytes = Vec::new();
    pk.serialize_compressed(&mut pk_bytes).expect("serialize pk");
    fs::write(&pk_path, pk_bytes).expect("write pk");

    let mut vk_bytes = Vec::new();
    vk.serialize_compressed(&mut vk_bytes).expect("serialize vk");
    fs::write(&vk_path, vk_bytes).expect("write vk");

    println!("Setup complete.");
    println!("  Proving key:      {}", pk_path.display());
    println!("  Verification key: {}", vk_path.display());
}

fn serialize_proof(proof: &Proof<Bn254>) -> String {
    let mut bytes = Vec::new();
    proof.serialize_compressed(&mut bytes).expect("serialize proof");
    hex::encode(bytes)
}

fn serialize_vk(vk: &ark_groth16::VerifyingKey<Bn254>) -> String {
    let mut bytes = Vec::new();
    vk.serialize_compressed(&mut bytes).expect("serialize vk");
    hex::encode(bytes)
}

fn run_hash_two(left: &str, right: &str) {
    let left_fr = Fr::from_str(left).unwrap_or_else(|_| {
        eprintln!("Invalid left field element: {}", left);
        std::process::exit(1);
    });
    let right_fr = Fr::from_str(right).unwrap_or_else(|_| {
        eprintln!("Invalid right field element: {}", right);
        std::process::exit(1);
    });
    let result = Poseidon::new().hash_two(&left_fr, &right_fr);
    println!("{}", result);
}

fn run_hash_fields(values: &[String]) {
    let fields: Vec<Fr> = values
        .iter()
        .map(|s| {
            Fr::from_str(s).unwrap_or_else(|_| {
                eprintln!("Invalid field element: {}", s);
                std::process::exit(1);
            })
        })
        .collect();
    let result = Poseidon::new().hash(&fields);
    println!("{}", result);
}

fn deserialize_proof(hex_str: &str) -> Proof<Bn254> {
    let bytes = hex::decode(hex_str.trim_start_matches("0x")).expect("bad proof hex");
    Proof::<Bn254>::deserialize_compressed(&bytes[..]).expect("deserialize proof")
}

fn run_prove(circuit: &str, inputs_path: &Path, out_path: Option<&Path>) {
    let (pk_path, vk_path) = key_paths(circuit);
    if !pk_path.exists() || !vk_path.exists() {
        eprintln!("No keys found for '{}'. Run: apx-zk setup {}", circuit, circuit);
        std::process::exit(1);
    }

    let inputs = load_json(inputs_path);
    let built = build_circuit(circuit, &inputs);

    let pk = load_proving_key(pk_path.to_str().unwrap()).expect("load pk");
    let vk = load_verification_key(vk_path.to_str().unwrap()).expect("load vk");

    println!("APX-ZK — Proving circuit: {}", circuit);
    let (proof, valid) = built.prove(&pk, &vk);
    let proof_hex = serialize_proof(&proof);

    let vk_hex = serialize_vk(&vk);

    let result = serde_json::json!({
        "circuit": circuit,
        "status": if valid { "VERIFIED" } else { "INVALID" },
        "verification_result": valid,
        "proof_hex": proof_hex,
        "vk_hex": vk_hex,
        "public_inputs": inputs,
    });

    let out = out_path
        .map(|p| p.to_path_buf())
        .unwrap_or_else(|| inputs_path.with_file_name(format!("{}_proof.json", circuit)));

    fs::write(&out, serde_json::to_string_pretty(&result).unwrap()).expect("write proof");
    println!("Proof written to: {}", out.display());
    println!(
        "Verification: {}",
        if valid { "VALID" } else { "INVALID" }
    );
}

fn run_verify(circuit: &str, inputs_path: &Path) {
    let inputs = load_json(inputs_path);
    let proof_hex = inputs
        .get("proof_hex")
        .and_then(|v| v.as_str())
        .unwrap_or_else(|| {
            eprintln!("verify requires proof_hex in inputs JSON");
            std::process::exit(1);
        });

    let built = build_circuit(circuit, &inputs);
    let public_inputs = built.public_inputs();

    let (_, vk_path) = key_paths(circuit);
    if !vk_path.exists() {
        eprintln!("No verification key for '{}'. Run: apx-zk setup {}", circuit, circuit);
        std::process::exit(1);
    }

    let vk = load_verification_key(vk_path.to_str().unwrap()).expect("load vk");
    let proof = deserialize_proof(proof_hex);

    let valid = Groth16::<Bn254>::verify(&vk, &public_inputs, &proof).unwrap_or(false);

    println!("APX-ZK — Verifying circuit: {}", circuit);
    println!("Result: {}", if valid { "VALID" } else { "INVALID" });

    if !valid {
        std::process::exit(1);
    }
}

#[cfg(test)]
mod json_witness_tests {
    use super::*;
    use ark_relations::r1cs::{ConstraintSynthesizer, ConstraintSystem};

    fn batch_merkle_satisfied(v: &Value) -> bool {
        let circuit = BatchMerkleCircuit {
            merkle_root: json_fr(v, "merkle_root"),
            entity_count: json_fr(v, "entity_count"),
            leaves: json_fr_array::<4>(v, "leaves"),
            path_elements: json_fr_matrix::<4, 8>(v, "path_elements"),
            path_indices: json_fr_matrix::<4, 8>(v, "path_indices"),
        };
        let cs = ConstraintSystem::<Fr>::new_ref();
        circuit.generate_constraints(cs.clone()).unwrap();
        cs.is_satisfied().unwrap()
    }

    #[test]
    fn batch_merkle_ec2_json_matches_hardcoded_witness() {
        let v: Value = serde_json::from_str(include_str!("../tests/fixtures/batch_merkle_ec2.json"))
            .expect("valid JSON");
        assert!(
            batch_merkle_satisfied(&v),
            "JSON-loaded ec2 witness should satisfy batch-merkle constraints"
        );
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        usage();
    }

    match args[1].as_str() {
        "setup" => {
            if args.len() < 3 {
                eprintln!("Usage: apx-zk setup <circuit>");
                std::process::exit(1);
            }
            let circuit = validate_circuit(&args[2]);
            run_setup(circuit);
        }
        "prove" => {
            if args.len() < 5 || args[3] != "--inputs" {
                eprintln!("Usage: apx-zk prove <circuit> --inputs <inputs.json> [--out <proof.json>]");
                std::process::exit(1);
            }
            let circuit = validate_circuit(&args[2]);
            let inputs_path = Path::new(&args[4]);
            let out_path = if args.len() >= 7 && args[5] == "--out" {
                Some(Path::new(&args[6]))
            } else {
                None
            };
            run_prove(circuit, inputs_path, out_path);
        }
        "verify" => {
            if args.len() < 5 || args[3] != "--inputs" {
                eprintln!("Usage: apx-zk verify <circuit> --inputs <inputs.json>");
                std::process::exit(1);
            }
            let circuit = validate_circuit(&args[2]);
            let inputs_path = Path::new(&args[4]);
            run_verify(circuit, inputs_path);
        }
        "hash-two" => {
            if args.len() < 4 {
                eprintln!("Usage: apx-zk hash-two <left_decimal> <right_decimal>");
                std::process::exit(1);
            }
            run_hash_two(&args[2], &args[3]);
        }
        "hash-fields" => {
            if args.len() < 3 {
                eprintln!("Usage: apx-zk hash-fields <decimal> [<decimal> ...]");
                std::process::exit(1);
            }
            run_hash_fields(&args[2..].to_vec());
        }
        _ => usage(),
    }
}