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
pub struct ThreatCircuit {
    // Public inputs
    pub threat_score: Fr,
    pub policy_id: Fr,
    
    // Private witness
    pub original_hash: Fr,
    pub mitigated_hash: Fr,
}

impl ConstraintSynthesizer<Fr> for ThreatCircuit {
    fn generate_constraints(self, cs: ConstraintSystemRef<Fr>) -> Result<(), SynthesisError> {
        // Allocate public inputs
        let threat_score_var = FpVar::new_input(cs.clone(), || Ok(self.threat_score))?;
        let policy_id_var = FpVar::new_input(cs.clone(), || Ok(self.policy_id))?;
        
        // Allocate private witness
        let original_hash_var = FpVar::new_witness(cs.clone(), || Ok(self.original_hash))?;
        let mitigated_hash_var = FpVar::new_witness(cs.clone(), || Ok(self.mitigated_hash))?;
        
        // ===== CONSTRAINT 1: Policy ID must be valid (1, 2, or 3) =====
        
        // Part A: policyId >= 1
        // GreaterEqThan(policyId, 1) is implemented as LessEqThan(1, policyId)
        // Which is LessThan(1, policyId + 1), i.e., 1 < policyId + 1
        // This means: (1 + 256 - (policyId + 1)) = (256 - policyId)
        // Check if bit 8 is 1 (meaning 1 >= policyId, which we want to be false)
        // So we want bit 8 to be 1 for valid policyId >= 1
        
        // Simpler approach: policyId must NOT be zero
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
        
        // Part B: policyId <= 3 (LessEqThan implementation)
        // LessEqThan(a, N) = LessThan(a, N+1): offset = 256 - (N+1) = 256 - 4 = 252
        let policy_upper_offset = &policy_id_var + FpVar::constant(Fr::from(252u64)); // 256 - 4
        let policy_upper_bits = policy_upper_offset.to_bits_le()?;
        
        // Check bit 8 is 0 (meaning policyId < 4, i.e. policyId <= 3)
        policy_upper_bits[8].enforce_equal(&Boolean::FALSE)?;
        
        // ===== CONSTRAINT 2: Threat score must be valid (0-100) =====
        // LessEqThan(threatScore, 100) = LessThan(threatScore, 101): offset = 256 - 101 = 155
        let score_offset = &threat_score_var + FpVar::constant(Fr::from(155u64)); // 256 - 101
        let score_bits = score_offset.to_bits_le()?;
        
        // Check bit 8 is 0 (meaning threatScore < 101, i.e. threatScore <= 100)
        score_bits[8].enforce_equal(&Boolean::FALSE)?;
        
        // ===== CONSTRAINT 3: If threat detected, hashes must differ =====
        
        // IsZero(threatScore)
        let threat_inv = FpVar::new_witness(cs.clone(), || {
            let threat_val = threat_score_var.value()?;
            if !threat_val.is_zero() {
                Ok(threat_val.inverse().unwrap())
            } else {
                Ok(Fr::from(0u64))
            }
        })?;
        
        let is_threat_zero = (&threat_score_var * &threat_inv * Fr::from(-1i64)) + FpVar::constant(Fr::from(1u64));
        
        // Enforce: in * out === 0
        let threat_zero_check = &threat_score_var * &is_threat_zero;
        threat_zero_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // IsEqual(originalHash, mitigatedHash)
        let hash_diff = &mitigated_hash_var - &original_hash_var;
        
        let hash_inv = FpVar::new_witness(cs.clone(), || {
            let diff_val = hash_diff.value()?;
            if !diff_val.is_zero() {
                Ok(diff_val.inverse().unwrap())
            } else {
                Ok(Fr::from(0u64))
            }
        })?;
        
        let are_hashes_equal = (&hash_diff * &hash_inv * Fr::from(-1i64)) + FpVar::constant(Fr::from(1u64));
        
        // Enforce: in * out === 0
        let hash_zero_check = &hash_diff * &are_hashes_equal;
        hash_zero_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // mitigationCheck = hashesEqual.out * (1 - isThreatZero.out)
        // If threat > 0 AND hashes same → fail
        let one_minus_threat_zero = FpVar::constant(Fr::from(1u64)) - &is_threat_zero;
        let mitigation_check = &are_hashes_equal * &one_minus_threat_zero;
        
        // Enforce: mitigationCheck === 0
        mitigation_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
        // ===== CONSTRAINT 4: High threats require action =====
        
        // GreaterThan(threatScore, 70): threatScore > 70
        // Implemented as LessThan(70, threatScore + 1)
        // Which means: 70 < threatScore, i.e., 71 <= threatScore
        // LessThan(70, threatScore) computes: (70 + 256 - threatScore)
        // If bit 8 is 0, then 70 < threatScore (threatScore > 70)
        
        let high_threat_offset = FpVar::constant(Fr::from(256u64 + 70u64)) - &threat_score_var;
        let high_threat_bits = high_threat_offset.to_bits_le()?;
        
        // LessThan(70, threatScore): compute 70 + 256 - threatScore.
        // bit 8 = 0 means 70 < threatScore (high threat).
        // Invert: is_high_threat = 1 when bit 8 = 0 (i.e. NOT bit 8).
        let is_high_threat_bool = high_threat_bits[8].not();
        
        // Convert boolean to field element
        let is_high_threat_fp = is_high_threat_bool.select(
            &FpVar::constant(Fr::from(1u64)),
            &FpVar::constant(Fr::from(0u64))
        )?;
        
        // LessEqThan(policyId, 2): policyId <= 2
        // Compute policyId + 256 - 3. Bit 8 = 0 means policyId < 3, i.e. policyId <= 2.
        // Invert: is_policy_action = 1 when bit 8 = 0 (i.e. NOT bit 8).
        let policy_action_offset = &policy_id_var + FpVar::constant(Fr::from(253u64)); // 256 - 3
        let policy_action_bits = policy_action_offset.to_bits_le()?;
        
        let is_policy_action_bool = policy_action_bits[8].not();
        
        let is_policy_action_fp = is_policy_action_bool.select(
            &FpVar::constant(Fr::from(1u64)),
            &FpVar::constant(Fr::from(0u64))
        )?;
        
        let one_minus_policy_action = FpVar::constant(Fr::from(1u64)) - &is_policy_action_fp;
        let policy_check = &is_high_threat_fp * &one_minus_policy_action;
        
        // Enforce: policyCheck === 0
        policy_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        
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
    fn test_threat_low_score_logging() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Low threat (score=30), logging only (policy=3), hashes differ
        let circuit = ThreatCircuit {
            threat_score: Fr::from(30u64),
            policy_id: Fr::from(3u64),      // Log only
            original_hash: Fr::from(111111u64),
            mitigated_hash: Fr::from(222222u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Low threat with logging should satisfy");
        println!("✓ Low threat with logging test passed");
        println!("  Constraints: {}", cs.num_constraints());
        println!("  Variables: {}", cs.num_instance_variables() + cs.num_witness_variables());
    }
    
    #[test]
    fn test_threat_high_score_blocked() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // High threat (score=95), blocked (policy=1), hashes differ
        let circuit = ThreatCircuit {
            threat_score: Fr::from(95u64),
            policy_id: Fr::from(1u64),      // Block
            original_hash: Fr::from(111111u64),
            mitigated_hash: Fr::from(222222u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "High threat with blocking should satisfy");
        println!("✓ High threat with blocking test passed");
    }
    
    #[test]
    fn test_threat_high_score_rate_limited() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // High threat (score=80), rate-limited (policy=2), hashes differ
        let circuit = ThreatCircuit {
            threat_score: Fr::from(80u64),
            policy_id: Fr::from(2u64),      // Rate-limit
            original_hash: Fr::from(111111u64),
            mitigated_hash: Fr::from(222222u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "High threat with rate-limit should satisfy");
        println!("✓ High threat with rate-limiting test passed");
    }
    
    #[test]
    fn test_threat_zero_score() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // No threat (score=0), any policy, hashes can be same
        let circuit = ThreatCircuit {
            threat_score: Fr::from(0u64),
            policy_id: Fr::from(3u64),
            original_hash: Fr::from(111111u64),
            mitigated_hash: Fr::from(111111u64), // Same allowed when score=0
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Zero threat should satisfy");
        println!("✓ Zero threat test passed");
    }
    
    #[test]
    fn test_threat_invalid_policy() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Invalid policy ID (0 or >3)
        let circuit = ThreatCircuit {
            threat_score: Fr::from(50u64),
            policy_id: Fr::from(4u64),      // INVALID
            original_hash: Fr::from(111111u64),
            mitigated_hash: Fr::from(222222u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), "Invalid policy should be rejected");
        println!("✓ Invalid policy correctly rejected");
    }
    
    #[test]
    fn test_threat_high_score_no_action() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // High threat (score=90) but only logging (policy=3) - should fail
        let circuit = ThreatCircuit {
            threat_score: Fr::from(90u64),
            policy_id: Fr::from(3u64),      // INVALID: logging only for high threat
            original_hash: Fr::from(111111u64),
            mitigated_hash: Fr::from(222222u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), 
            "High threat without action should be rejected");
        println!("✓ High threat without action correctly rejected");
    }
    
    #[test]
    fn test_threat_score_boundary() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // Boundary case: score=70 (not high), policy=3 allowed  
        // Note: >70 means 71 and above, so 70 should NOT trigger high threat logic
        let circuit = ThreatCircuit {
            threat_score: Fr::from(70u64),
            policy_id: Fr::from(3u64),      // OK: not > 70
            original_hash: Fr::from(111111u64),
            mitigated_hash: Fr::from(222222u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        // Check constraints status
        let satisfied = cs.is_satisfied().unwrap();
        if !satisfied {
            println!("FAILED: Constraints not satisfied for score=70");
            println!("Num constraints: {}", cs.num_constraints());
            // Try with different hash values
        }
        
        assert!(satisfied, "Boundary score=70 should satisfy");
        println!("✓ Boundary score test passed");
    }
    
    #[test]
    fn test_threat_score_71() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        // score=71 IS high (>70), so policy must be 1 or 2
        let circuit = ThreatCircuit {
            threat_score: Fr::from(71u64),
            policy_id: Fr::from(2u64),      // OK: action taken
            original_hash: Fr::from(111111u64),
            mitigated_hash: Fr::from(222222u64),
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Score=71 with action should satisfy");
        println!("✓ Score 71 with action test passed");
    }
}
