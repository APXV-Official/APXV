// Copyright 2026 APXVdev
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

//! Groth16 key generation for APX entity circuits (BN254).

use ark_bn254::{Bn254, Fr};
use ark_groth16::{Groth16, ProvingKey, VerifyingKey};
use ark_relations::r1cs::ConstraintSynthesizer;
use ark_serialize::{CanonicalDeserialize, CanonicalSerialize};
use std::fs::File;
use std::io::{Read, Write};
use std::path::Path;

use crate::circuits::{
    batch_merkle::BatchMerkleCircuit,
    compliance::ComplianceCircuit,
    core_redaction::CoreRedactionCircuit,
    merkle_inclusion::MerkleInclusionCircuit,
    normalization::NormalizationCircuit,
    redaction_v1::RedactionProofV1Circuit,
    threat::ThreatCircuit,
    voice_redaction::VoiceRedactionCircuit,
};
use crate::poseidon::Poseidon;

/// Generate proving and verification keys for a circuit and persist to disk.
pub fn generate_keys<C>(
    circuit: C,
    pk_path: &str,
    vk_path: &str,
) -> Result<(ProvingKey<Bn254>, VerifyingKey<Bn254>), Box<dyn std::error::Error>>
where
    C: ConstraintSynthesizer<Fr>,
{
    println!("Generating keys for circuit...");

    let mut rng = rand::thread_rng();
    let pk = Groth16::<Bn254>::generate_random_parameters_with_reduction(circuit, &mut rng)?;
    let vk = pk.vk.clone();

    println!("  Keys generated");

    let mut pk_bytes = Vec::new();
    pk.serialize_compressed(&mut pk_bytes)?;

    if let Some(parent) = Path::new(pk_path).parent() {
        std::fs::create_dir_all(parent)?;
    }

    let mut pk_file = File::create(pk_path)?;
    pk_file.write_all(&pk_bytes)?;
    println!("  Proving key saved to: {}", pk_path);

    let mut vk_bytes = Vec::new();
    vk.serialize_compressed(&mut vk_bytes)?;

    if let Some(parent) = Path::new(vk_path).parent() {
        std::fs::create_dir_all(parent)?;
    }

    let mut vk_file = File::create(vk_path)?;
    vk_file.write_all(&vk_bytes)?;
    println!("  Verification key saved to: {}", vk_path);

    Ok((pk, vk))
}

/// Load proving key from file.
pub fn load_proving_key(path: &str) -> Result<ProvingKey<Bn254>, Box<dyn std::error::Error>> {
    let mut file = File::open(path)?;
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)?;
    Ok(ProvingKey::<Bn254>::deserialize_compressed(&bytes[..])?)
}

/// Load verification key from file.
pub fn load_verification_key(path: &str) -> Result<VerifyingKey<Bn254>, Box<dyn std::error::Error>> {
    let mut file = File::open(path)?;
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)?;
    Ok(VerifyingKey::<Bn254>::deserialize_compressed(&bytes[..])?)
}

/// Generate Groth16 keys for all 8 entity circuits.
pub fn apx_generate_all_keys(output_dir: &str) -> Result<(), Box<dyn std::error::Error>> {
    println!("\n=== APX ZK Key Generation ===");
    println!("Generating Groth16 keys for all 8 circuits...\n");

    println!("[1/8] Normalization Circuit");
    let norm_circuit = NormalizationCircuit {
        original_hash: Fr::from(1u64),
        normalized_hash: Fr::from(2u64),
        feature_bitmap: Fr::from(127u64),
        entropy_drop: Fr::from(50u64),
        original_length: Fr::from(1000u64),
        normalized_length: Fr::from(900u64),
        feature_count: Fr::from(5u64),
    };
    generate_keys(
        norm_circuit,
        &format!("{}/normalization.pk", output_dir),
        &format!("{}/normalization.vk", output_dir),
    )?;

    println!("\n[2/8] Core Redaction Circuit");
    let core_circuit = CoreRedactionCircuit {
        merkle_root: Fr::from(12345u64),
        entity_count: Fr::from(10u64),
        original_data_hash: Fr::from(111111u64),
        redacted_data_hash: Fr::from(222222u64),
    };
    generate_keys(
        core_circuit,
        &format!("{}/core-redaction.pk", output_dir),
        &format!("{}/core-redaction.vk", output_dir),
    )?;

    println!("\n[3/8] Compliance Circuit");
    let compliance_circuit = ComplianceCircuit {
        entity_count: Fr::from(5u64),
        policy_id: Fr::from(3u64),
        original_hash: Fr::from(111111u64),
        redacted_hash: Fr::from(222222u64),
    };
    generate_keys(
        compliance_circuit,
        &format!("{}/compliance.pk", output_dir),
        &format!("{}/compliance.vk", output_dir),
    )?;

    println!("\n[4/8] Threat Circuit");
    let threat_circuit = ThreatCircuit {
        threat_score: Fr::from(80u64),
        policy_id: Fr::from(2u64),
        original_hash: Fr::from(111111u64),
        mitigated_hash: Fr::from(222222u64),
    };
    generate_keys(
        threat_circuit,
        &format!("{}/threat.pk", output_dir),
        &format!("{}/threat.vk", output_dir),
    )?;

    println!("\n[5/8] Voice Redaction Circuit");
    let voice_circuit = VoiceRedactionCircuit {
        entity_count: Fr::from(3u64),
        policy_id: Fr::from(3u64),
        original_hash: Fr::from(111111u64),
        redacted_hash: Fr::from(222222u64),
    };
    generate_keys(
        voice_circuit,
        &format!("{}/voice-redaction.pk", output_dir),
        &format!("{}/voice-redaction.vk", output_dir),
    )?;

    println!("\n[6/8] Redaction Proof V1 Circuit");
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
    let poseidon = Poseidon::new();
    let digest = poseidon.hash(&leaf_commitments.to_vec());

    let redaction_v1_circuit = RedactionProofV1Circuit {
        merkle_root: Fr::from(99999u64),
        entity_count: Fr::from(8u64),
        entities_digest: digest,
        original_data_hash: Fr::from(111111u64),
        redacted_data_hash: Fr::from(222222u64),
        leaf_commitments,
    };
    generate_keys(
        redaction_v1_circuit,
        &format!("{}/redaction-v1.pk", output_dir),
        &format!("{}/redaction-v1.vk", output_dir),
    )?;

    println!("\n[7/8] Merkle Inclusion Circuit");
    let merkle_circuit = MerkleInclusionCircuit {
        merkle_root: Fr::from(12345u64),
        leaf: Fr::from(1000u64),
        path_elements: [Fr::from(2000u64); 8],
        path_indices: [Fr::from(0u64); 8],
    };
    generate_keys(
        merkle_circuit,
        &format!("{}/merkle-inclusion.pk", output_dir),
        &format!("{}/merkle-inclusion.vk", output_dir),
    )?;

    println!("\n[8/8] Batch Merkle Circuit");
    let batch_circuit = BatchMerkleCircuit {
        merkle_root: Fr::from(12345u64),
        entity_count: Fr::from(4u64),
        leaves: [Fr::from(1000u64); 4],
        path_elements: [[Fr::from(0u64); 8]; 4],
        path_indices: [[Fr::from(0u64); 8]; 4],
    };
    generate_keys(
        batch_circuit,
        &format!("{}/batch-merkle.pk", output_dir),
        &format!("{}/batch-merkle.vk", output_dir),
    )?;

    println!("\nAll 8 circuit keys generated successfully!");
    println!("Keys saved to: {}/", output_dir);

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::circuits::normalization::NormalizationCircuit;
    use tempfile::TempDir;

    #[test]
    fn test_generate_and_load_normalization_keys() {
        let temp_dir = TempDir::new().unwrap();
        let temp_path = temp_dir.path().to_str().unwrap();

        let circuit = NormalizationCircuit {
            original_hash: Fr::from(1u64),
            normalized_hash: Fr::from(2u64),
            feature_bitmap: Fr::from(127u64),
            entropy_drop: Fr::from(50u64),
            original_length: Fr::from(1000u64),
            normalized_length: Fr::from(900u64),
            feature_count: Fr::from(5u64),
        };

        let pk_path = format!("{}/test.pk", temp_path);
        let vk_path = format!("{}/test.vk", temp_path);

        let (pk_orig, vk_orig) = generate_keys(circuit, &pk_path, &vk_path).unwrap();
        let pk_loaded = load_proving_key(&pk_path).unwrap();
        let vk_loaded = load_verification_key(&vk_path).unwrap();

        assert_eq!(pk_orig.vk.alpha_g1, pk_loaded.vk.alpha_g1);
        assert_eq!(vk_orig.alpha_g1, vk_loaded.alpha_g1);
    }
}