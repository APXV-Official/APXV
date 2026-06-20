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
use crate::poseidon_gadget::PoseidonGadget;

const MERKLE_DEPTH: usize = 8;    // Supports up to 256 entities (2^8) per document
const BATCH_SIZE: usize = 4;      // Verify 4 leaves at once

#[derive(Clone)]
pub struct BatchMerkleCircuit {
    // Public inputs
    pub merkle_root: Fr,
    pub entity_count: Fr,
    
    // Private witness
    pub leaves: [Fr; BATCH_SIZE],
    pub path_elements: [[Fr; MERKLE_DEPTH]; BATCH_SIZE],
    pub path_indices: [[Fr; MERKLE_DEPTH]; BATCH_SIZE],
}

impl ConstraintSynthesizer<Fr> for BatchMerkleCircuit {
    fn generate_constraints(self, cs: ConstraintSystemRef<Fr>) -> Result<(), SynthesisError> {
        // Allocate public inputs
        let merkle_root_var = FpVar::new_input(cs.clone(), || Ok(self.merkle_root))?;
        let entity_count_var = FpVar::new_input(cs.clone(), || Ok(self.entity_count))?;
        
        // ===== ENTITY COUNT VALIDATION =====
        
        // Count must be > 0
        let count_inv = FpVar::new_witness(cs.clone(), || {
            let count_val = entity_count_var.value()?;
            if !count_val.is_zero() {
                Ok(count_val.inverse().unwrap())
            } else {
                Ok(Fr::from(0u64))
            }
        })?;
        
        let is_count_zero = (&entity_count_var * &count_inv * Fr::from(-1i64)) + FpVar::constant(Fr::from(1u64));
        let count_zero_check = &entity_count_var * &is_count_zero;
        count_zero_check.enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        is_count_zero.enforce_equal(&FpVar::constant(Fr::from(0u64)))?; // Count must NOT be zero
        
        // Count must be <= BATCH_SIZE
        // Use LessEqThan: entityCount + (256 - (BATCH_SIZE + 1))
        let count_upper_offset = &entity_count_var + FpVar::constant(Fr::from((256 - (BATCH_SIZE + 1)) as u64));
        
        // Decompose to bits
        let count_upper_bits = count_upper_offset.to_bits_le()?;
        
        // Bit 8 must be 0 (means count <= BATCH_SIZE)
        assert!(count_upper_bits.len() > 8, "bit decomposition returned fewer than 9 bits — BATCH_SIZE upper bound constraint cannot be applied");
        count_upper_bits[8].enforce_equal(&Boolean::FALSE)?;
        
        // ===== VERIFY EACH LEAF =====
        
        for batch_idx in 0..BATCH_SIZE {
            // Allocate leaf
            let leaf_var = FpVar::new_witness(cs.clone(), || Ok(self.leaves[batch_idx]))?;
            
            // Allocate path
            let mut path_element_vars = Vec::new();
            // BUG-G FIX: allocate path indices as Boolean (enforces b ∈ {0,1})
            // instead of FpVar::new_witness (unconstrained field element).
            let mut path_index_bits: Vec<Boolean<Fr>> = Vec::new();
            
            for depth_idx in 0..MERKLE_DEPTH {
                let elem_var = FpVar::new_witness(cs.clone(), || {
                    Ok(self.path_elements[batch_idx][depth_idx])
                })?;
                path_element_vars.push(elem_var);
                
                // BUG-G FIX: Boolean::new_witness adds the constraint b*(1-b)=0
                let bit = Boolean::<Fr>::new_witness(cs.clone(), || {
                    Ok(!self.path_indices[batch_idx][depth_idx].is_zero())
                })?;
                path_index_bits.push(bit);
            }
            
            // Compute Merkle root for this leaf

            // One gadget per leaf (reused across levels for this leaf)
            let poseidon = PoseidonGadget::new();

            // Bug #18 fix: domain-separate leaves from internal nodes.
            // Compute leaf_hash = Poseidon(LEAF_DOMAIN=1, raw_leaf) before
            // entering the path loop, matching PoseidonMerkleTree.buildTree().
            let leaf_domain = FpVar::constant(Fr::from(1u64));
            let mut current_hash = poseidon.hash_two(&leaf_domain, &leaf_var);
            for depth_idx in 0..MERKLE_DEPTH {
                let path_idx = &path_index_bits[depth_idx];  // Boolean<Fr>
                let sibling  = &path_element_vars[depth_idx];
                
                // Constrained mux via Boolean::conditionally_select:
                //   path_idx=1 (true)  → left=sibling,      right=current
                //   path_idx=0 (false) → left=current_hash, right=sibling
                let left_input  = FpVar::conditionally_select(path_idx, sibling, &current_hash)?;
                let right_input = FpVar::conditionally_select(path_idx, &current_hash, sibling)?;
                
                // BUG-H FIX: PoseidonGadget emits R1CS constraints linking
                // current_hash to left_input and right_input.  The old
                // FpVar::new_witness approach only set the native witness value
                // without any constraint, letting a malicious prover choose
                // current_hash freely at every level.
                current_hash = poseidon.hash_two(&left_input, &right_input);
            }
            
            // Verify this leaf's computed root matches the public root
            current_hash.enforce_equal(&merkle_root_var)?;
        }
        
        // ===== OUTPUT =====
        let all_valid = FpVar::constant(Fr::from(1u64));
        all_valid.enforce_equal(&FpVar::constant(Fr::from(1u64)))?;
        
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ark_relations::r1cs::ConstraintSystem;
    use crate::poseidon::Poseidon;
    
    /// Build a Merkle tree with 4 unique leaves, padded to BATCH_SIZE (32) by
    /// duplicating the first leaf with its valid path for unused circuit slots.
    fn build_batch_tree() -> (Fr, [Fr; BATCH_SIZE], [[Fr; MERKLE_DEPTH]; BATCH_SIZE], [[Fr; MERKLE_DEPTH]; BATCH_SIZE]) {
        let poseidon = Poseidon::new();
        let leaf_domain = Fr::from(1u64);
        // PADDING_SENTINEL = Poseidon(LEAF_DOMAIN, 0xDEADBEEF) — matches TypeScript PADDING_CONST
        let padding_sentinel = poseidon.hash_two(&leaf_domain, &Fr::from(0xDEADBEEFu64));
        
        // Create 4 unique leaves (raw commitment values)
        let unique_leaves = [
            Fr::from(1001u64),
            Fr::from(2002u64),
            Fr::from(3003u64),
            Fr::from(4004u64),
        ];
        
        // Level 0: domain-separate every leaf — Poseidon(1, raw)
        let level0: [Fr; 4] = [
            poseidon.hash_two(&leaf_domain, &unique_leaves[0]),
            poseidon.hash_two(&leaf_domain, &unique_leaves[1]),
            poseidon.hash_two(&leaf_domain, &unique_leaves[2]),
            poseidon.hash_two(&leaf_domain, &unique_leaves[3]),
        ];
        
        // Level 1: 2 nodes (pairs of domain-separated leaves)
        let level1 = [
            poseidon.hash_two(&level0[0], &level0[1]),
            poseidon.hash_two(&level0[2], &level0[3]),
        ];
        
        // Level 2: 1 node
        let level2_0 = poseidon.hash_two(&level1[0], &level1[1]);
        
        // Upper levels (2..MERKLE_DEPTH): hash with padding_sentinel
        let mut current = level2_0;
        for _ in 2..MERKLE_DEPTH {
            current = poseidon.hash_two(&current, &padding_sentinel);
        }
        let root = current;
        
        // Build paths for all 4 unique leaves
        let mut all_path_elements = [[Fr::zero(); MERKLE_DEPTH]; BATCH_SIZE];
        let mut all_path_indices = [[Fr::zero(); MERKLE_DEPTH]; BATCH_SIZE];
        
        for i in 0..4 {
            // Level 0: sibling is the adjacent domain-separated leaf
            all_path_elements[i][0] = if i % 2 == 0 { level0[i + 1] } else { level0[i - 1] };
            all_path_indices[i][0] = Fr::from((i % 2) as u64);
            
            // Level 1: sibling is the adjacent level1 node
            let level1_idx = i / 2;
            all_path_elements[i][1] = if level1_idx % 2 == 0 { level1[level1_idx + 1] } else { level1[level1_idx - 1] };
            all_path_indices[i][1] = Fr::from((level1_idx % 2) as u64);
            
            // Upper levels: sibling is padding_sentinel
            for j in 2..MERKLE_DEPTH {
                all_path_elements[i][j] = padding_sentinel;
                all_path_indices[i][j] = Fr::from(0u64);
            }
        }
        
        // Build full BATCH_SIZE leaves array; padding slots 4..BATCH_SIZE use
        // leaf[0] and its path (as recommended in the circuit comment).
        let mut all_leaves = [unique_leaves[0]; BATCH_SIZE];
        for i in 0..4 {
            all_leaves[i] = unique_leaves[i];
        }
        let path0  = all_path_elements[0];
        let index0 = all_path_indices[0];
        for i in 4..BATCH_SIZE {
            all_path_elements[i] = path0;
            all_path_indices[i]  = index0;
        }
        
        (root, all_leaves, all_path_elements, all_path_indices)
    }
    
    #[test]
    fn test_batch_merkle_valid() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        let (root, leaves, path_elements, path_indices) = build_batch_tree();
        
        let circuit = BatchMerkleCircuit {
            merkle_root: root,
            entity_count: Fr::from(4u64),
            leaves,
            path_elements,
            path_indices,
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Valid batch Merkle proof should satisfy");
        println!("✓ Valid batch Merkle proof test passed");
        println!("  Constraints: {}", cs.num_constraints());
        println!("  Variables: {}", cs.num_instance_variables() + cs.num_witness_variables());
    }
    
    #[test]
    fn test_batch_merkle_zero_count() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        let (root, leaves, path_elements, path_indices) = build_batch_tree();
        
        let circuit = BatchMerkleCircuit {
            merkle_root: root,
            entity_count: Fr::from(0u64), // INVALID
            leaves,
            path_elements,
            path_indices,
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), "Zero count should be rejected");
        println!("✓ Zero count correctly rejected");
    }
    
    #[test]
    fn test_batch_merkle_count_too_large() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        let (root, leaves, path_elements, path_indices) = build_batch_tree();
        
        let circuit = BatchMerkleCircuit {
            merkle_root: root,
            entity_count: Fr::from(5u64), // INVALID: > BATCH_SIZE (4)
            leaves,
            path_elements,
            path_indices,
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), "Count > batch size should be rejected");
        println!("✓ Count too large correctly rejected");
    }
    
    #[test]
    fn test_batch_merkle_wrong_leaf() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        let (root, mut leaves, path_elements, path_indices) = build_batch_tree();
        
        // Corrupt one leaf
        leaves[3] = Fr::from(99999u64);
        
        let circuit = BatchMerkleCircuit {
            merkle_root: root,
            entity_count: Fr::from(4u64),
            leaves, // INVALID
            path_elements,
            path_indices,
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), "Wrong leaf should be rejected");
        println!("✓ Wrong leaf correctly rejected");
    }
    
    #[test]
    fn test_batch_merkle_wrong_root() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        let (_root, leaves, path_elements, path_indices) = build_batch_tree();
        
        let circuit = BatchMerkleCircuit {
            merkle_root: Fr::from(99999u64), // INVALID
            entity_count: Fr::from(4u64),
            leaves,
            path_elements,
            path_indices,
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), "Wrong root should be rejected");
        println!("✓ Wrong root correctly rejected");
    }
}
