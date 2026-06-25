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

#[derive(Clone)]
pub struct CoreRedactionCircuit {
    // Public inputs
    pub merkle_root: Fr,
    pub entity_count: Fr,
    
    // Private witness
    pub original_data_hash: Fr,
    pub redacted_data_hash: Fr,
}

impl ConstraintSynthesizer<Fr> for CoreRedactionCircuit {
    fn generate_constraints(self, cs: ConstraintSystemRef<Fr>) -> Result<(), SynthesisError> {
        // Allocate public inputs
        let merkle_root_var = FpVar::new_input(cs.clone(), || Ok(self.merkle_root))?;
        let entity_count_var = FpVar::new_input(cs.clone(), || Ok(self.entity_count))?;
        
        // Allocate private witness
        let original_hash_var = FpVar::new_witness(cs.clone(), || Ok(self.original_data_hash))?;
        let redacted_hash_var = FpVar::new_witness(cs.clone(), || Ok(self.redacted_data_hash))?;
        
        // ===== CONSTRAINT 1: Entity count must be > 0 =====
        // IsZero(entityCount) should output 0 (meaning entityCount is NOT zero)
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
        let count_check = &entity_count_var * &is_count_zero;
        count_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // Enforce: is_count_zero.out === 0 (count must NOT be zero)
        is_count_zero.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // ===== CONSTRAINT 2: Merkle root must be non-zero =====
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
        let merkle_check = &merkle_root_var * &is_merkle_zero;
        merkle_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // Enforce: is_merkle_zero.out === 0 (merkle must NOT be zero)
        is_merkle_zero.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // ===== CONSTRAINT 3: Data hashes must differ =====
        // IsEqual(originalDataHash, redactedDataHash) should output 0 (meaning NOT equal)
        
        // IsEqual is implemented as IsZero(in[1] - in[0])
        let hash_diff = &redacted_hash_var - &original_hash_var;
        
        let hash_inv = FpVar::new_witness(cs.clone(), || {
            let diff_val = hash_diff.value()?;
            if !diff_val.is_zero() {
                Ok(diff_val.inverse().unwrap())
            } else {
                Ok(Fr::from(0u64))
            }
        })?;
        
        // IsZero gadget: out = -in*inv + 1
        let are_hashes_equal = (&hash_diff * &hash_inv * Fr::from(-1i64)) + FpVar::constant(Fr::from(1u64));
        
        // Enforce: in * out === 0
        let hash_check = &hash_diff * &are_hashes_equal;
        hash_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // Enforce: are_hashes_equal.out === 0 (hashes must NOT be equal)
        are_hashes_equal.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // ===== OUTPUT =====
        // All constraints passed, output valid = 1
        let valid = FpVar::constant(Fr::from(1u64));
        valid.enforce_equal(&FpVar::constant(Fr::from(1u64)))?;
        
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ark_relations::r1cs::ConstraintSystem;
    
    #[test]
    fn test_core_redaction_valid() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Valid case: all constraints satisfied
        let circuit = CoreRedactionCircuit {
            merkle_root: Fr::from(123456789u64),      // Non-zero
            entity_count: Fr::from(5u64),             // > 0
            original_data_hash: Fr::from(111111u64),  // Different from redacted
            redacted_data_hash: Fr::from(222222u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Valid redaction should satisfy constraints");
        println!("✓ Valid core redaction test passed");
        println!("  Constraints: {}", cs.num_constraints());
        println!("  Variables: {}", cs.num_instance_variables() + cs.num_witness_variables());
    }
    
    #[test]
    fn test_core_redaction_zero_count() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Invalid: entity count is zero
        let circuit = CoreRedactionCircuit {
            merkle_root: Fr::from(123456789u64),
            entity_count: Fr::from(0u64),             // INVALID: must be > 0
            original_data_hash: Fr::from(111111u64),
            redacted_data_hash: Fr::from(222222u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        assert!(!cs.is_satisfied().unwrap(), "Should NOT be satisfied with zero count");
        println!("✓ Zero count correctly rejected");
    }
    
    #[test]
    fn test_core_redaction_zero_merkle() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Invalid: merkle root is zero
        let circuit = CoreRedactionCircuit {
            merkle_root: Fr::from(0u64),              // INVALID: must be non-zero
            entity_count: Fr::from(5u64),
            original_data_hash: Fr::from(111111u64),
            redacted_data_hash: Fr::from(222222u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        assert!(!cs.is_satisfied().unwrap(), "Should NOT be satisfied with zero merkle root");
        println!("✓ Zero merkle root correctly rejected");
    }
    
    #[test]
    fn test_core_redaction_equal_hashes() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Invalid: hashes are equal (no redaction occurred)
        let circuit = CoreRedactionCircuit {
            merkle_root: Fr::from(123456789u64),
            entity_count: Fr::from(5u64),
            original_data_hash: Fr::from(111111u64),
            redacted_data_hash: Fr::from(111111u64),  // INVALID: same as original
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        assert!(!cs.is_satisfied().unwrap(), "Should NOT be satisfied with equal hashes");
        println!("✓ Equal hashes correctly rejected");
    }
    
    #[test]
    fn test_core_redaction_large_values() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Test with large field elements
        use std::str::FromStr;

        let large_merkle = Fr::from_str("123456789012345678901234567890").unwrap();
        
        let large_hash1 = Fr::from_str("987654321098765432109876543210").unwrap();
        
        let large_hash2 = Fr::from_str("111222333444555666777888999000").unwrap();
        
        let circuit = CoreRedactionCircuit {
            merkle_root: large_merkle,
            entity_count: Fr::from(100u64),
            original_data_hash: large_hash1,
            redacted_data_hash: large_hash2,
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Large values should work");
        println!("✓ Large values test passed");
    }
}
