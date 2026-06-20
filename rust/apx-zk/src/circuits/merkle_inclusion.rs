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
use ark_std::Zero;
use ark_r1cs_std::prelude::*;
use ark_r1cs_std::fields::fp::FpVar;
use ark_relations::r1cs::{ConstraintSynthesizer, ConstraintSystemRef, SynthesisError};
use crate::poseidon_gadget::PoseidonGadget;

const MERKLE_DEPTH: usize = 8;  // Supports up to 256 entities (2^8) per document

#[derive(Clone)]
pub struct MerkleInclusionCircuit {
    // Public input
    pub merkle_root: Fr,
    
    // Private witness
    pub leaf: Fr,
    pub path_elements: [Fr; MERKLE_DEPTH],
    pub path_indices: [Fr; MERKLE_DEPTH], // 0 or 1
}

impl ConstraintSynthesizer<Fr> for MerkleInclusionCircuit {
    fn generate_constraints(self, cs: ConstraintSystemRef<Fr>) -> Result<(), SynthesisError> {
        // Allocate public input
        let merkle_root_var = FpVar::new_input(cs.clone(), || Ok(self.merkle_root))?;
        
        // Allocate private witness
        let leaf_var = FpVar::new_witness(cs.clone(), || Ok(self.leaf))?;
        
        let mut path_element_vars = Vec::new();
        for i in 0..MERKLE_DEPTH {
            let elem_var = FpVar::new_witness(cs.clone(), || Ok(self.path_elements[i]))?;
            path_element_vars.push(elem_var);
        }
        
        // BUG-A FIX: allocate path indices as Boolean so they are constrained
        // to {0, 1} via the R1CS constraint  b * (1 - b) = 0.
        // Previously they were FpVar::new_witness (unconstrained field elements),
        // which let a malicious prover supply non-binary values and break the mux.
        let mut path_index_bits: Vec<Boolean<Fr>> = Vec::new();
        for i in 0..MERKLE_DEPTH {
            let bit = Boolean::<Fr>::new_witness(cs.clone(), || {
                Ok(!self.path_indices[i].is_zero())
            })?;
            path_index_bits.push(bit);
        }
        
        // ===== MERKLE PATH VERIFICATION =====
        // Start with the leaf and hash up the tree

        // One gadget instance is reused for every level (the parameters are the
        // same for every hash call — reusing avoids re-loading constants).
        let poseidon = PoseidonGadget::new();

        // Bug #18 fix: domain-separate leaves from internal nodes.
        // Compute leaf_hash = Poseidon(LEAF_DOMAIN=1, raw_leaf) before entering
        // the path loop. This matches the TypeScript PoseidonMerkleTree which
        // stores Poseidon(1, raw_commitment) at tree level 0, preventing
        // second-preimage attacks where a padding or internal-node value could
        // be presented as a valid leaf witness.
        let leaf_domain = FpVar::constant(Fr::from(1u64));
        let mut current_hash = poseidon.hash_two(&leaf_domain, &leaf_var);
        for i in 0..MERKLE_DEPTH {
            let path_idx = &path_index_bits[i];  // Boolean<Fr>
            let sibling  = &path_element_vars[i];
            
            // Multiplexer logic using Boolean::conditionally_select:
            //   conditionally_select(cond, true_val, false_val)
            //   → when path_idx = 1 (true):  left = sibling,       right = current
            //   → when path_idx = 0 (false): left = current_hash,  right = sibling
            // i.e. pathIndex 0 → current is left child; 1 → current is right child.
            let left_input  = FpVar::conditionally_select(path_idx, sibling, &current_hash)?;
            let right_input = FpVar::conditionally_select(path_idx, &current_hash, sibling)?;
            
            // BUG-H FIX: use PoseidonGadget instead of FpVar::new_witness.
            // PoseidonGadget::hash_two emits R1CS multiplication constraints that
            // LINK current_hash to left_input and right_input.  With the old
            // FpVar::new_witness approach the closure only set the native witness
            // value — zero constraints connected the hash output to its inputs,
            // so a malicious prover could set current_hash to any field element.
            current_hash = poseidon.hash_two(&left_input, &right_input);
        }
        
        // ===== FINAL CONSTRAINT =====
        // The computed root MUST equal the public root
        current_hash.enforce_equal(&merkle_root_var)?;
        
        // If we reach here, the proof is valid
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
    
    /// Build a simple Merkle tree for testing
    /// Returns (root, leaves, path_elements, path_indices for leaf 0)
    fn build_test_tree() -> (Fr, Vec<Fr>, [Fr; MERKLE_DEPTH], [Fr; MERKLE_DEPTH]) {
        let poseidon = Poseidon::new();
        let leaf_domain = Fr::from(1u64);
        // PADDING_SENTINEL = Poseidon(LEAF_DOMAIN, 0xDEADBEEF) — matches TypeScript PADDING_CONST
        let padding_sentinel = poseidon.hash_two(&leaf_domain, &Fr::from(0xDEADBEEFu64));
        
        // Create 4 leaves (raw commitment values)
        let leaves = vec![
            Fr::from(1000u64),
            Fr::from(2000u64),
            Fr::from(3000u64),
            Fr::from(4000u64),
        ];
        
        // Level 0: domain-separate every leaf — Poseidon(1, raw)
        let level0: Vec<Fr> = leaves.iter().map(|l| poseidon.hash_two(&leaf_domain, l)).collect();
        
        // Level 1: [hash(level0[0], level0[1]), hash(level0[2], level0[3])]
        let level1_0 = poseidon.hash_two(&level0[0], &level0[1]);
        let level1_1 = poseidon.hash_two(&level0[2], &level0[3]);
        
        // Level 2: [hash(level1_0, level1_1)]
        let level2_0 = poseidon.hash_two(&level1_0, &level1_1);
        
        // Upper levels (2..MERKLE_DEPTH): hash current root with padding_sentinel
        let mut current = level2_0;
        for _ in 2..MERKLE_DEPTH {
            current = poseidon.hash_two(&current, &padding_sentinel);
        }
        let root = current;
        
        // Build path for leaf 0 (raw value 1000)
        let mut path_elements = [Fr::zero(); MERKLE_DEPTH];
        let mut path_indices = [Fr::zero(); MERKLE_DEPTH];
        
        // Level 0: leaf 0 is LEFT child; sibling is domain-hashed leaf 1
        path_elements[0] = level0[1]; // Poseidon(1, 2000)
        path_indices[0] = Fr::from(0u64);
        
        // Level 1: level1_0 is LEFT child; sibling is level1_1
        path_elements[1] = level1_1;
        path_indices[1] = Fr::from(0u64);
        
        // Upper levels: sibling is padding_sentinel
        for i in 2..MERKLE_DEPTH {
            path_elements[i] = padding_sentinel;
            path_indices[i] = Fr::from(0u64);
        }
        
        (root, leaves, path_elements, path_indices)
    }
    
    #[test]
    fn test_merkle_inclusion_valid() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        let (root, leaves, path_elements, path_indices) = build_test_tree();
        
        let circuit = MerkleInclusionCircuit {
            merkle_root: root,
            leaf: leaves[0], // Prove leaf 0 is in the tree
            path_elements,
            path_indices,
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(cs.is_satisfied().unwrap(), "Valid Merkle inclusion should satisfy");
        println!("✓ Valid Merkle inclusion test passed");
        println!("  Constraints: {}", cs.num_constraints());
        println!("  Variables: {}", cs.num_instance_variables() + cs.num_witness_variables());
    }
    
    #[test]
    fn test_merkle_inclusion_wrong_leaf() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        let (root, _leaves, path_elements, path_indices) = build_test_tree();
        
        let circuit = MerkleInclusionCircuit {
            merkle_root: root,
            leaf: Fr::from(9999u64), // INVALID: leaf not in tree
            path_elements,
            path_indices,
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), "Wrong leaf should be rejected");
        println!("✓ Wrong leaf correctly rejected");
    }
    
    #[test]
    fn test_merkle_inclusion_wrong_root() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        let (_root, leaves, path_elements, path_indices) = build_test_tree();
        
        let circuit = MerkleInclusionCircuit {
            merkle_root: Fr::from(12345u64), // INVALID: wrong root
            leaf: leaves[0],
            path_elements,
            path_indices,
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), "Wrong root should be rejected");
        println!("✓ Wrong root correctly rejected");
    }
    
    #[test]
    fn test_merkle_inclusion_wrong_path() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        
        let (root, leaves, mut path_elements, path_indices) = build_test_tree();
        
        // Corrupt the path
        path_elements[0] = Fr::from(99999u64);
        
        let circuit = MerkleInclusionCircuit {
            merkle_root: root,
            leaf: leaves[0],
            path_elements, // INVALID: corrupted path
            path_indices,
        };
        
        circuit.generate_constraints(cs.clone()).unwrap();
        
        assert!(!cs.is_satisfied().unwrap(), "Wrong path should be rejected");
        println!("✓ Wrong path correctly rejected");
    }
}
