// Copyright 2026 apxv1dev
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
pub struct ComplianceCircuit {
    // Public inputs
    pub entity_count: Fr,
    pub policy_id: Fr,
    
    // Private witness
    pub original_hash: Fr,
    pub redacted_hash: Fr,
}

impl ConstraintSynthesizer<Fr> for ComplianceCircuit {
    fn generate_constraints(self, cs: ConstraintSystemRef<Fr>) -> Result<(), SynthesisError> {
        // Allocate public inputs
        let entity_count_var = FpVar::new_input(cs.clone(), || Ok(self.entity_count))?;
        let policy_id_var = FpVar::new_input(cs.clone(), || Ok(self.policy_id))?;
        
        // Allocate private witness
        let original_hash_var = FpVar::new_witness(cs.clone(), || Ok(self.original_hash))?;
        let redacted_hash_var = FpVar::new_witness(cs.clone(), || Ok(self.redacted_hash))?;
        
        // ===== CONSTRAINT 1: Entity count >= 0 =====
        // (Always satisfied for field elements, no constraint needed)
        
        // ===== CONSTRAINT 2: Policy ID must be valid (1-5) =====
        
        // Part A: policyId <= 5 (using LessEqThan logic)
        // LessEqThan checks if in[0] <= in[1], implemented as LessThan(in[0], in[1]+1)
        // We want: policyId <= 5
        // So we check: policyId < 6
        
        // LessThan(a, b) computes: (a + 2^n - b) and checks if bit n is 0
        // For n=8 (handles values up to 255): a < b iff bit 8 of (a + 256 - b) is 0
        
        // Compute: policyId + 256 - 6 = policyId + 250
        let policy_offset = &policy_id_var + FpVar::constant(Fr::from(250u64)); // 256 - 6
        
        // Decompose to bits (need 9 bits for n+1 where n=8)
        let policy_bits = policy_offset.to_bits_le()?;
        
        // Check that bit 8 (index 8) is 0, meaning policyId < 6 (i.e., policyId <= 5)
        assert!(policy_bits.len() > 8, "bit decomposition too short for policy ID upper-bound check");
        policy_bits[8].enforce_equal(&Boolean::FALSE)?;
        
        // Part B: policyId must be non-zero (IsZero check)
        let policy_inv = FpVar::new_witness(cs.clone(), || {
            let policy_val = policy_id_var.value()?;
            if !policy_val.is_zero() {
                Ok(policy_val.inverse().unwrap())
            } else {
                Ok(Fr::from(0u64))
            }
        })?;
        
        // IsZero gadget: out = -in*inv + 1
        let is_policy_zero = (&policy_id_var * &policy_inv * Fr::from(-1i64)) + FpVar::constant(Fr::from(1u64));
        
        // Enforce: in * out === 0
        let policy_zero_check = &policy_id_var * &is_policy_zero;
        policy_zero_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // Enforce: is_policy_zero.out === 0 (policy must NOT be zero)
        is_policy_zero.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // ===== CONSTRAINT 3: Hash difference check (conditional on entityCount) =====
        
        // IsEqual(originalHash, redactedHash)
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
        
        // IsZero(entityCount)
        let count_inv = FpVar::new_witness(cs.clone(), || {
            let count_val = entity_count_var.value()?;
            if !count_val.is_zero() {
                Ok(count_val.inverse().unwrap())
            } else {
                Ok(Fr::from(0u64))
            }
        })?;
        
        // IsZero gadget: is_entity_zero.out = 1 if zero, 0 if non-zero
        let is_entity_zero = (&entity_count_var * &count_inv * Fr::from(-1i64)) + FpVar::constant(Fr::from(1u64));
        
        // Enforce: in * out === 0
        let count_zero_check = &entity_count_var * &is_entity_zero;
        count_zero_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // Compute: hashCheck = hashesEqual.out * (1 - isEntityZero.out)
        // If entities > 0 (isEntityZero=0): hashCheck = hashesEqual * 1 = hashesEqual
        // If entities = 0 (isEntityZero=1): hashCheck = hashesEqual * 0 = 0
        let one_minus_entity_zero = FpVar::constant(Fr::from(1u64)) - &is_entity_zero;
        let hash_check = &are_hashes_equal * &one_minus_entity_zero;
        
        // Enforce: hashCheck === 0
        // If entities > 0: hashes must be different (hashesEqual must be 0)
        // If entities = 0: constraint always satisfied (hashCheck = 0)
        hash_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
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
    fn test_compliance_valid_with_redaction() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Valid case: entities redacted, hashes differ, valid policy
        let circuit = ComplianceCircuit {
            entity_count: Fr::from(5u64),
            policy_id: Fr::from(2u64),         // GDPR
            original_hash: Fr::from(111111u64),
            redacted_hash: Fr::from(222222u64), // Different
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Valid compliance should satisfy");
        println!("✓ Valid compliance with redaction test passed");
        println!("  Constraints: {}", cs.num_constraints());
        println!("  Variables: {}", cs.num_instance_variables() + cs.num_witness_variables());
    }
    
    #[test]
    fn test_compliance_no_pii() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Valid case: no PII found (entityCount=0), hashes can be same
        let circuit = ComplianceCircuit {
            entity_count: Fr::from(0u64),       // No entities
            policy_id: Fr::from(3u64),          // HIPAA
            original_hash: Fr::from(111111u64),
            redacted_hash: Fr::from(111111u64), // Same (allowed when count=0)
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "No PII case should satisfy");
        println!("✓ No PII (same hashes) test passed");
    }
    
    #[test]
    fn test_compliance_all_policy_ids() {
        // Test all valid policy IDs (1-5)
        for policy_id in 1..=5 {
            let cs = ConstraintSystem::<Fr>::new_ref();
            
            let circuit = ComplianceCircuit {
                entity_count: Fr::from(1u64),
                policy_id: Fr::from(policy_id),
                original_hash: Fr::from(111111u64),
                redacted_hash: Fr::from(222222u64),
            };
            
            circuit.generate_constraints(cs.clone()).unwrap();
            
            assert!(cs.is_satisfied().unwrap(), 
                "Policy ID {} should be valid", policy_id);
        }
        println!("✓ All policy IDs (1-5) test passed");
    }
    
    #[test]
    fn test_compliance_invalid_policy_zero() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Invalid: policy ID is 0
        let circuit = ComplianceCircuit {
            entity_count: Fr::from(5u64),
            policy_id: Fr::from(0u64),          // INVALID
            original_hash: Fr::from(111111u64),
            redacted_hash: Fr::from(222222u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), "Policy ID 0 should be rejected");
        println!("✓ Invalid policy ID 0 correctly rejected");
    }
    
    #[test]
    fn test_compliance_invalid_policy_too_high() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Invalid: policy ID > 5
        let circuit = ComplianceCircuit {
            entity_count: Fr::from(5u64),
            policy_id: Fr::from(6u64),          // INVALID (> 5)
            original_hash: Fr::from(111111u64),
            redacted_hash: Fr::from(222222u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), "Policy ID 6 should be rejected");
        println!("✓ Invalid policy ID 6 correctly rejected");
    }
    
    #[test]
    fn test_compliance_invalid_same_hashes_with_entities() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Invalid: entities > 0 but hashes are same (no redaction)
        let circuit = ComplianceCircuit {
            entity_count: Fr::from(5u64),       // Has entities
            policy_id: Fr::from(2u64),
            original_hash: Fr::from(111111u64),
            redacted_hash: Fr::from(111111u64), // INVALID: same when count > 0
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), 
            "Same hashes with entities > 0 should be rejected");
        println!("✓ Same hashes with entities correctly rejected");
    }
}
