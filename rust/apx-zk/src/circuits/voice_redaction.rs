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
pub struct VoiceRedactionCircuit {
    // Public inputs
    pub entity_count: Fr,
    pub policy_id: Fr,
    
    // Private witness
    pub original_hash: Fr,
    pub redacted_hash: Fr,
}

impl ConstraintSynthesizer<Fr> for VoiceRedactionCircuit {
    fn generate_constraints(self, cs: ConstraintSystemRef<Fr>) -> Result<(), SynthesisError> {
        // Allocate public inputs
        let entity_count_var = FpVar::new_input(cs.clone(), || Ok(self.entity_count))?;
        let policy_id_var = FpVar::new_input(cs.clone(), || Ok(self.policy_id))?;
        
        // Allocate private witness
        let original_hash_var = FpVar::new_witness(cs.clone(), || Ok(self.original_hash))?;
        let redacted_hash_var = FpVar::new_witness(cs.clone(), || Ok(self.redacted_hash))?;
        
        // ===== CONSTRAINT 1: Policy ID must be valid (1, 2, 3, or 4) =====
        
        // Part A: policyId >= 1 (must be non-zero)
        let policy_nonzero_inv = FpVar::new_witness(cs.clone(), || {
            let policy_val = policy_id_var.value()?;
            if !policy_val.is_zero() {
                Ok(policy_val.inverse().unwrap())
            } else {
                Ok(Fr::from(0u64))
            }
        })?;
        
        let is_policy_zero = (&policy_id_var * &policy_nonzero_inv * Fr::from(-1i64)) + FpVar::constant(Fr::from(1u64));
        
        // Enforce: in * out === 0
        let policy_nonzero_check = &policy_id_var * &is_policy_zero;
        policy_nonzero_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // Enforce: is_policy_zero === 0 (policy must NOT be zero)
        is_policy_zero.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // Part B: policyId <= 4 (LessEqThan implementation)
        // LessEqThan(a, b) checks a <= b, implemented as LessThan(a, b+1)
        // For policyId <= 4, check policyId < 5
        // LessThan: (policyId + 256 - 5) and check bit 8 == 0
        let policy_upper_offset = &policy_id_var + FpVar::constant(Fr::from(251u64)); // 256 - 5
        let policy_upper_bits = policy_upper_offset.to_bits_le()?;
        
        // Check bit 8 is 0 (meaning policyId < 5, i.e., policyId <= 4)
        policy_upper_bits[8].enforce_equal(&Boolean::FALSE)?;
        
        // ===== CONSTRAINT 2: Check if this is redaction policy (policyId == 3) =====
        // IsEqual(policyId, 3)
        let policy_diff = &policy_id_var - FpVar::constant(Fr::from(3u64));
        
        let policy_diff_inv = FpVar::new_witness(cs.clone(), || {
            let diff_val = policy_diff.value()?;
            if !diff_val.is_zero() {
                Ok(diff_val.inverse().unwrap())
            } else {
                Ok(Fr::from(0u64))
            }
        })?;
        
        // is_redaction_policy.out = 1 if policyId == 3, else 0
        let is_redaction_policy = (&policy_diff * &policy_diff_inv * Fr::from(-1i64)) + FpVar::constant(Fr::from(1u64));
        
        // Enforce: in * out === 0
        let policy_eq_check = &policy_diff * &is_redaction_policy;
        policy_eq_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // ===== CONSTRAINT 3: Check if hashes are equal =====
        let hash_diff = &redacted_hash_var - &original_hash_var;
        
        let hash_inv = FpVar::new_witness(cs.clone(), || {
            let diff_val = hash_diff.value()?;
            if !diff_val.is_zero() {
                Ok(diff_val.inverse().unwrap())
            } else {
                Ok(Fr::from(0u64))
            }
        })?;
        
        // are_hashes_equal.out = 1 if hashes equal, else 0
        let are_hashes_equal = (&hash_diff * &hash_inv * Fr::from(-1i64)) + FpVar::constant(Fr::from(1u64));
        
        // Enforce: in * out === 0
        let hash_zero_check = &hash_diff * &are_hashes_equal;
        hash_zero_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // ===== CONSTRAINT 4: Check if entityCount is zero =====
        let count_inv = FpVar::new_witness(cs.clone(), || {
            let count_val = entity_count_var.value()?;
            if !count_val.is_zero() {
                Ok(count_val.inverse().unwrap())
            } else {
                Ok(Fr::from(0u64))
            }
        })?;
        
        // is_entity_zero.out = 1 if entityCount == 0, else 0
        let is_entity_zero = (&entity_count_var * &count_inv * Fr::from(-1i64)) + FpVar::constant(Fr::from(1u64));
        
        // Enforce: in * out === 0
        let count_zero_check = &entity_count_var * &is_entity_zero;
        count_zero_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // ===== CONSTRAINT 5: Enforce hash difference based on policy =====
        // Logic: hashesEqual.out must be 0 UNLESS (isRedactionPolicy AND isEntityZero)
        // Constraint: hashesEqual.out * (1 - isRedactionPolicy.out * isEntityZero.out) === 0
        
        // allowSameHash = isRedactionPolicy.out * isEntityZero.out
        // allowSameHash = 1 only if policyId == 3 AND entityCount == 0
        let allow_same_hash = &is_redaction_policy * &is_entity_zero;
        
        // hashConstraint = hashesEqual.out * (1 - allowSameHash)
        // hashConstraint = 1 if hashes same AND not allowed → fail
        let one_minus_allow = FpVar::constant(Fr::from(1u64)) - &allow_same_hash;
        let hash_constraint = &are_hashes_equal * &one_minus_allow;
        
        // Enforce: hashConstraint === 0
        hash_constraint.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
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
    
    #[test]
    fn test_voice_transcription() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Policy 1 (STT), hashes must differ
        let circuit = VoiceRedactionCircuit {
            entity_count: Fr::from(100u64),
            policy_id: Fr::from(1u64),          // Transcription
            original_hash: Fr::from(111111u64),
            redacted_hash: Fr::from(222222u64), // Different
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Transcription should satisfy");
        println!("✓ Voice transcription test passed");
        println!("  Constraints: {}", cs.num_constraints());
        println!("  Variables: {}", cs.num_instance_variables() + cs.num_witness_variables());
    }
    
    #[test]
    fn test_voice_synthesis() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Policy 2 (TTS), hashes must differ
        let circuit = VoiceRedactionCircuit {
            entity_count: Fr::from(50u64),
            policy_id: Fr::from(2u64),          // Synthesis
            original_hash: Fr::from(111111u64),
            redacted_hash: Fr::from(333333u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Synthesis should satisfy");
        println!("✓ Voice synthesis test passed");
    }
    
    #[test]
    fn test_voice_redaction_with_entities() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Policy 3 (redaction), entities > 0, hashes must differ
        let circuit = VoiceRedactionCircuit {
            entity_count: Fr::from(10u64),      // Has entities
            policy_id: Fr::from(3u64),          // Redaction
            original_hash: Fr::from(111111u64),
            redacted_hash: Fr::from(444444u64), // Different
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Redaction with entities should satisfy");
        println!("✓ Voice redaction with entities test passed");
    }
    
    #[test]
    fn test_voice_redaction_no_pii() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Policy 3 (redaction), entityCount=0, hashes CAN be same
        let circuit = VoiceRedactionCircuit {
            entity_count: Fr::from(0u64),       // No PII found
            policy_id: Fr::from(3u64),          // Redaction
            original_hash: Fr::from(111111u64),
            redacted_hash: Fr::from(111111u64), // Same (allowed)
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Redaction with no PII should satisfy");
        println!("✓ Voice redaction no PII test passed");
    }
    
    #[test]
    fn test_voice_vault_storage() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Policy 4 (vault), hashes must differ
        let circuit = VoiceRedactionCircuit {
            entity_count: Fr::from(200u64),
            policy_id: Fr::from(4u64),          // Vault
            original_hash: Fr::from(111111u64),
            redacted_hash: Fr::from(555555u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Vault storage should satisfy");
        println!("✓ Voice vault storage test passed");
    }
    
    #[test]
    fn test_voice_invalid_policy_zero() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Invalid policy ID (0)
        let circuit = VoiceRedactionCircuit {
            entity_count: Fr::from(10u64),
            policy_id: Fr::from(0u64),          // INVALID
            original_hash: Fr::from(111111u64),
            redacted_hash: Fr::from(222222u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), "Policy 0 should be rejected");
        println!("✓ Invalid policy 0 correctly rejected");
    }
    
    #[test]
    fn test_voice_invalid_policy_too_high() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Invalid policy ID (> 4)
        let circuit = VoiceRedactionCircuit {
            entity_count: Fr::from(10u64),
            policy_id: Fr::from(5u64),          // INVALID
            original_hash: Fr::from(111111u64),
            redacted_hash: Fr::from(222222u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), "Policy 5 should be rejected");
        println!("✓ Invalid policy 5 correctly rejected");
    }
    
    #[test]
    fn test_voice_invalid_same_hash_non_redaction() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Policy 1 (not redaction), hashes must differ
        let circuit = VoiceRedactionCircuit {
            entity_count: Fr::from(10u64),
            policy_id: Fr::from(1u64),          // Transcription
            original_hash: Fr::from(111111u64),
            redacted_hash: Fr::from(111111u64), // INVALID: same
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), 
            "Same hashes for non-redaction policy should be rejected");
        println!("✓ Same hashes for policy 1 correctly rejected");
    }
    
    #[test]
    fn test_voice_invalid_redaction_same_hash_with_entities() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Policy 3 (redaction), entities > 0, but hashes same
        let circuit = VoiceRedactionCircuit {
            entity_count: Fr::from(10u64),      // Has entities
            policy_id: Fr::from(3u64),          // Redaction
            original_hash: Fr::from(111111u64),
            redacted_hash: Fr::from(111111u64), // INVALID: same
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), 
            "Redaction with entities but same hashes should be rejected");
        println!("✓ Redaction with entities and same hashes correctly rejected");
    }
}
