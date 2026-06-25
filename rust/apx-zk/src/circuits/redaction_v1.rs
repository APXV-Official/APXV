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
use ark_bn254::Fr;
use ark_ff::Field;
use ark_std::Zero;
use ark_r1cs_std::prelude::*;
use ark_r1cs_std::fields::fp::FpVar;
use ark_relations::r1cs::{ConstraintSynthesizer, ConstraintSystemRef, SynthesisError};
use crate::poseidon_gadget::PoseidonGadget;

#[derive(Clone)]
pub struct RedactionProofV1Circuit {
    // Public inputs
    pub merkle_root: Fr,
    pub entity_count: Fr,
    pub entities_digest: Fr,
    
    // Private witness
    pub original_data_hash: Fr,
    pub redacted_data_hash: Fr,
    pub leaf_commitments: [Fr; 8],
}

impl ConstraintSynthesizer<Fr> for RedactionProofV1Circuit {
    fn generate_constraints(self, cs: ConstraintSystemRef<Fr>) -> Result<(), SynthesisError> {
        // Allocate public inputs
        let merkle_root_var = FpVar::new_input(cs.clone(), || Ok(self.merkle_root))?;
        let entity_count_var = FpVar::new_input(cs.clone(), || Ok(self.entity_count))?;
        let entities_digest_var = FpVar::new_input(cs.clone(), || Ok(self.entities_digest))?;
        
        // Allocate public inputs — document hashes are public so verifiers can bind
        // the proof to a specific document without trusting external infrastructure.
        let original_hash_var = FpVar::new_input(cs.clone(), || Ok(self.original_data_hash))?;
        let redacted_hash_var = FpVar::new_input(cs.clone(), || Ok(self.redacted_data_hash))?;
        
        let mut leaf_commitment_vars = Vec::new();
        for i in 0..8 {
            let leaf_var = FpVar::new_witness(cs.clone(), || Ok(self.leaf_commitments[i]))?;
            leaf_commitment_vars.push(leaf_var);
        }
        
        // ===== CONSTRAINT 1: Merkle root is non-zero =====
        let merkle_inv = FpVar::new_witness(cs.clone(), || {
            let merkle_val = merkle_root_var.value()?;
            if !merkle_val.is_zero() {
                Ok(merkle_val.inverse().unwrap())
            } else {
                Ok(Fr::from(0u64))
            }
        })?;
        
        // IsZero gadget: out = -in*inv + 1
        let is_merkle_zero = (&merkle_root_var * &merkle_inv * Fr::from(-1i64)) + FpVar::constant(Fr::from(1u64));
        
        // Enforce: in * out === 0
        let merkle_zero_check = &merkle_root_var * &is_merkle_zero;
        merkle_zero_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // Enforce: is_merkle_zero === 0 (merkle must NOT be zero)
        is_merkle_zero.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // ===== CONSTRAINT 2: Entity count is > 0 =====
        let count_inv = FpVar::new_witness(cs.clone(), || {
            let count_val = entity_count_var.value()?;
            if !count_val.is_zero() {
                Ok(count_val.inverse().unwrap())
            } else {
                Ok(Fr::from(0u64))
            }
        })?;
        
        // IsZero gadget: out = -in*inv + 1
        let is_count_zero = (&entity_count_var * &count_inv * Fr::from(-1i64)) + FpVar::constant(Fr::from(1u64));
        
        // Enforce: in * out === 0
        let count_zero_check = &entity_count_var * &is_count_zero;
        count_zero_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // Enforce: is_count_zero === 0 (count must NOT be zero)
        is_count_zero.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // ===== CONSTRAINT 3: Document was modified =====
        let hash_diff = &redacted_hash_var - &original_hash_var;
        
        let hash_inv = FpVar::new_witness(cs.clone(), || {
            let diff_val = hash_diff.value()?;
            if !diff_val.is_zero() {
                Ok(diff_val.inverse().unwrap())
            } else {
                Ok(Fr::from(0u64))
            }
        })?;
        
        // IsZero gadget: are_hashes_equal.out = 1 if equal, 0 if different
        let are_hashes_equal = (&hash_diff * &hash_inv * Fr::from(-1i64)) + FpVar::constant(Fr::from(1u64));
        
        // Enforce: in * out === 0
        let hash_zero_check = &hash_diff * &are_hashes_equal;
        hash_zero_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // Enforce: are_hashes_equal === 0 (hashes must NOT be equal)
        are_hashes_equal.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // ===== CONSTRAINT 4: Entities digest matches =====
        // BUG-H FIX: Use PoseidonGadget to compute the digest in-circuit so
        // that R1CS constraints link the result to the leaf_commitment_vars.
        // The old FpVar::new_witness approach only set the native value in the
        // closure — a malicious prover could set the digest to any field element.
        let poseidon = PoseidonGadget::new();
        
        // Sequential absorption matching native Poseidon::hash for 8 inputs:
        //   current = hash(leaf[0], leaf[1])
        //   current = hash(current, leaf[2])  ...  through leaf[7]
        let mut computed_digest = poseidon.hash_two(&leaf_commitment_vars[0], &leaf_commitment_vars[1]);
        for i in 2..8 {
            computed_digest = poseidon.hash_two(&computed_digest, &leaf_commitment_vars[i]);
        }
        
        // Enforce: computed_digest === entities_digest (public input)
        computed_digest.enforce_equal(&entities_digest_var)?;
        
        // ===== OUTPUT =====
        let valid = FpVar::constant(Fr::from(1u64));
        valid.enforce_equal(&FpVar::constant(Fr::from(1u64)))?;
        
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ark_relations::r1cs::ConstraintSystem;
    use crate::poseidon::Poseidon;
    
    #[test]
    fn test_redaction_proof_v1_valid() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Create 8 leaf commitments (entity hashes)
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
        
        // Compute the digest using Poseidon
        let poseidon = Poseidon::new();
        let digest = poseidon.hash(&leaf_commitments.to_vec());
        
        let circuit = RedactionProofV1Circuit {
            merkle_root: Fr::from(99999u64),        // Non-zero
            entity_count: Fr::from(8u64),           // > 0
            entities_digest: digest,                 // Poseidon hash of leaves
            original_data_hash: Fr::from(111111u64),
            redacted_data_hash: Fr::from(222222u64), // Different
            leaf_commitments,
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Valid redaction proof v1 should satisfy");
        println!("✓ Valid redaction proof v1 test passed");
        println!("  Constraints: {}", cs.num_constraints());
        println!("  Variables: {}", cs.num_instance_variables() + cs.num_witness_variables());
    }
    
    #[test]
    fn test_redaction_proof_v1_zero_merkle() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        let leaf_commitments = [Fr::from(1000u64); 8];
        let poseidon = Poseidon::new();
        let digest = poseidon.hash(&leaf_commitments.to_vec());
        
        let circuit = RedactionProofV1Circuit {
            merkle_root: Fr::from(0u64),            // INVALID: zero
            entity_count: Fr::from(8u64),
            entities_digest: digest,
            original_data_hash: Fr::from(111111u64),
            redacted_data_hash: Fr::from(222222u64),
            leaf_commitments,
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), "Zero merkle root should be rejected");
        println!("✓ Zero merkle root correctly rejected");
    }
    
    #[test]
    fn test_redaction_proof_v1_zero_count() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        let leaf_commitments = [Fr::from(1000u64); 8];
        let poseidon = Poseidon::new();
        let digest = poseidon.hash(&leaf_commitments.to_vec());
        
        let circuit = RedactionProofV1Circuit {
            merkle_root: Fr::from(99999u64),
            entity_count: Fr::from(0u64),           // INVALID: zero
            entities_digest: digest,
            original_data_hash: Fr::from(111111u64),
            redacted_data_hash: Fr::from(222222u64),
            leaf_commitments,
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), "Zero entity count should be rejected");
        println!("✓ Zero entity count correctly rejected");
    }
    
    #[test]
    fn test_redaction_proof_v1_same_hashes() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        let leaf_commitments = [Fr::from(1000u64); 8];
        let poseidon = Poseidon::new();
        let digest = poseidon.hash(&leaf_commitments.to_vec());
        
        let circuit = RedactionProofV1Circuit {
            merkle_root: Fr::from(99999u64),
            entity_count: Fr::from(8u64),
            entities_digest: digest,
            original_data_hash: Fr::from(111111u64),
            redacted_data_hash: Fr::from(111111u64), // INVALID: same
            leaf_commitments,
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), "Same hashes should be rejected");
        println!("✓ Same hashes correctly rejected");
    }
    
    #[test]
    fn test_redaction_proof_v1_wrong_digest() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        let leaf_commitments = [Fr::from(1000u64); 8];
        let wrong_digest = Fr::from(12345u64); // Wrong digest
        
        let circuit = RedactionProofV1Circuit {
            merkle_root: Fr::from(99999u64),
            entity_count: Fr::from(8u64),
            entities_digest: wrong_digest,          // INVALID: doesn't match
            original_data_hash: Fr::from(111111u64),
            redacted_data_hash: Fr::from(222222u64),
            leaf_commitments,
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), "Wrong digest should be rejected");
        println!("✓ Wrong digest correctly rejected");
    }
    
    #[test]
    fn test_redaction_proof_v1_different_leaves() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Different leaf values (realistic case)
        let leaf_commitments = [
            Fr::from(10001u64),
            Fr::from(20002u64),
            Fr::from(30003u64),
            Fr::from(40004u64),
            Fr::from(50005u64),
            Fr::from(60006u64),
            Fr::from(70007u64),
            Fr::from(80008u64),
        ];
        
        let poseidon = Poseidon::new();
        let digest = poseidon.hash(&leaf_commitments.to_vec());
        
        let circuit = RedactionProofV1Circuit {
            merkle_root: Fr::from(123456789u64),
            entity_count: Fr::from(8u64),
            entities_digest: digest,
            original_data_hash: Fr::from(987654321u64),
            redacted_data_hash: Fr::from(123123123u64),
            leaf_commitments,
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Different leaves should work");
        println!("✓ Different leaves test passed");
    }
}
