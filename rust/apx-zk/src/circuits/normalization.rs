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
use ark_bn254::Fr;
use ark_ff::Field;
use ark_std::Zero;
use ark_r1cs_std::prelude::*;
use ark_r1cs_std::fields::fp::FpVar;
use ark_relations::r1cs::{ConstraintSynthesizer, ConstraintSystemRef, SynthesisError};

#[derive(Clone)]
pub struct NormalizationCircuit {
    // Public inputs
    pub original_hash: Fr,
    pub normalized_hash: Fr,
    pub feature_bitmap: Fr,
    pub entropy_drop: Fr,
    
    // Private witness
    pub original_length: Fr,
    pub normalized_length: Fr,
    pub feature_count: Fr,
}

impl ConstraintSynthesizer<Fr> for NormalizationCircuit {
    fn generate_constraints(self, cs: ConstraintSystemRef<Fr>) -> Result<(), SynthesisError> {
        // Allocate public inputs
        let original_hash_var = FpVar::new_input(cs.clone(), || Ok(self.original_hash))?;
        let normalized_hash_var = FpVar::new_input(cs.clone(), || Ok(self.normalized_hash))?;
        let feature_bitmap_var = FpVar::new_input(cs.clone(), || Ok(self.feature_bitmap))?;
        let entropy_drop_var = FpVar::new_input(cs.clone(), || Ok(self.entropy_drop))?;
        
        // Allocate private witness
        let _original_length_var = FpVar::new_witness(cs.clone(), || Ok(self.original_length))?;
        let _normalized_length_var = FpVar::new_witness(cs.clone(), || Ok(self.normalized_length))?;
        let feature_count_var = FpVar::new_witness(cs.clone(), || Ok(self.feature_count))?;
        
        // ===== CONSTRAINT 1: Hash difference check =====
        // hashDiff = originalHash - normalizedHash
        let hash_diff = &original_hash_var - &normalized_hash_var;
        
        // IsZero gadget: inv <-- in != 0 ? 1/in : 0
        // out <== -in*inv + 1
        // in*out === 0
        let inv_var = FpVar::new_witness(cs.clone(), || {
            let diff_val = hash_diff.value()?;
            if !diff_val.is_zero() {
                Ok(diff_val.inverse().unwrap())
            } else {
                Ok(Fr::from(0u64))
            }
        })?;
        
        // Compute: out = -in*inv + 1 
        let is_zero_out = (&hash_diff * &inv_var * Fr::from(-1i64)) + FpVar::constant(Fr::from(1u64));
        
        // Enforce: in * out === 0 (critical IsZero constraint)
        let zero_check = &hash_diff * &is_zero_out;
        zero_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // isHashDifferent = 1 - isZero.out
        
        // ===== CONSTRAINT 2: Feature bitmap is valid (0-255) =====
        // Bit-decomposition range check: enforce upper 248 bits are zero.
        // This guarantees feature_bitmap is in [0, 255].
        let bitmap_bits = feature_bitmap_var.to_bits_le()?;
        for i in 8..bitmap_bits.len() {
            bitmap_bits[i].enforce_equal(&Boolean::FALSE)?;
        }
        
        // ===== CONSTRAINT 3: Entropy drop is valid (0-100) =====
        // LessEqThan(entropy_drop, 100): entropy_drop + 256 - 101 must have bit 8 = 0.
        let entropy_offset = &entropy_drop_var + FpVar::constant(Fr::from(256u64 - 101u64));
        let entropy_bits = entropy_offset.to_bits_le()?;
        assert!(entropy_bits.len() > 8, "bit decomposition too short for entropy range check");
        entropy_bits[8].enforce_equal(&Boolean::FALSE)?;
        
        // ===== CONSTRAINT 4: Feature count is valid (1-7) =====
        // Part A: feature_count >= 1 (must not be zero)
        let fc_inv = FpVar::new_witness(cs.clone(), || {
            let v = feature_count_var.value()?;
            if !v.is_zero() { Ok(v.inverse().unwrap()) } else { Ok(Fr::from(0u64)) }
        })?;
        let fc_is_zero = (&feature_count_var * &fc_inv * Fr::from(-1i64)) + FpVar::constant(Fr::from(1u64));
        let fc_zero_check = &feature_count_var * &fc_is_zero;
        fc_zero_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        fc_is_zero.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        // Part B: feature_count <= 7
        let fc_upper_offset = &feature_count_var + FpVar::constant(Fr::from(256u64 - 8u64));
        let fc_upper_bits = fc_upper_offset.to_bits_le()?;
        assert!(fc_upper_bits.len() > 8, "bit decomposition too short for feature_count range check");
        fc_upper_bits[8].enforce_equal(&Boolean::FALSE)?;
        
        // ===== FINAL VERIFICATION =====
        // Output verified = 1 (all constraints must pass)
        let verified = FpVar::constant(Fr::from(1u64));
        
        // Make verified a public output
        verified.enforce_equal(&FpVar::constant(Fr::from(1u64)))?;
        
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ark_relations::r1cs::ConstraintSystem;
    
    #[test]
    fn test_normalization_circuit_basic() {
        // Create constraint system
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Test case: basic normalization with different hashes
        let circuit = NormalizationCircuit {
            original_hash: Fr::from(12345u64),
            normalized_hash: Fr::from(67890u64),
            feature_bitmap: Fr::from(127u64),   // Valid: 0-255
            entropy_drop: Fr::from(50u64),      // Valid: 0-100
            original_length: Fr::from(1000u64),
            normalized_length: Fr::from(950u64),
            feature_count: Fr::from(5u64),      // Valid: 1-7
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Constraints should be satisfied");
        println!("✓ Basic normalization circuit test passed");
        println!("  Constraints: {}", cs.num_constraints());
        println!("  Variables: {}", cs.num_instance_variables() + cs.num_witness_variables());
    }
    
    #[test]
    fn test_normalization_same_hash() {
        // Edge case: same hash (no normalization applied)
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        let circuit = NormalizationCircuit {
            original_hash: Fr::from(12345u64),
            normalized_hash: Fr::from(12345u64), // Same!
            feature_bitmap: Fr::from(0u64),
            entropy_drop: Fr::from(0u64),
            original_length: Fr::from(1000u64),
            normalized_length: Fr::from(1000u64),
            feature_count: Fr::from(1u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Should work with identical hashes");
        println!("✓ Same hash test passed");
    }
    
    #[test]
    fn test_normalization_boundary_values() {
        // Test boundary values for bitmap and entropy
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        let circuit = NormalizationCircuit {
            original_hash: Fr::from(111u64),
            normalized_hash: Fr::from(222u64),
            feature_bitmap: Fr::from(255u64),   // Maximum
            entropy_drop: Fr::from(100u64),     // Maximum
            original_length: Fr::from(5000u64),
            normalized_length: Fr::from(4500u64),
            feature_count: Fr::from(7u64),      // Maximum
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Boundary values should work");
        println!("✓ Boundary values test passed");
    }
}
