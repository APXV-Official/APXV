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

//! Poseidon hash implementation for BN254 (t=3, rf=8, rp=57).

use ark_bn254::Fr;
use ark_ff::PrimeField;
use ark_std::Zero;

use crate::poseidon_constants;

/// Poseidon hash parameters for BN254.
pub struct PoseidonParams {
    pub t: usize,
    pub rf: usize,
    pub rp: usize,
    pub round_constants: Vec<Vec<Fr>>,
    pub mds_matrix: Vec<Vec<Fr>>,
}

/// Poseidon hash state.
pub struct Poseidon {
    params: PoseidonParams,
}

impl Poseidon {
    /// Create new Poseidon hasher with standard parameters for BN254.
    /// t=3 (hash 2 inputs), rf=8, rp=57.
    pub fn new() -> Self {
        let params = PoseidonParams {
            t: 3,
            rf: 8,
            rp: 57,
            round_constants: poseidon_constants::get_round_constants(),
            mds_matrix: poseidon_constants::get_mds_matrix(),
        };
        Self { params }
    }

    /// Hash 2 field elements (most common case — Merkle tree nodes).
    pub fn hash_two(&self, left: &Fr, right: &Fr) -> Fr {
        self.hash(&[*left, *right])
    }

    /// Hash multiple field elements.
    /// For more than (t-1) inputs, uses sequential absorption.
    pub fn hash(&self, inputs: &[Fr]) -> Fr {
        let max_inputs = self.params.t - 1;

        if inputs.len() <= max_inputs {
            return self.hash_single(inputs);
        }

        let mut current_hash = self.hash_single(&inputs[0..max_inputs]);

        for i in max_inputs..inputs.len() {
            current_hash = self.hash_single(&[current_hash, inputs[i]]);
        }

        current_hash
    }

    fn hash_single(&self, inputs: &[Fr]) -> Fr {
        assert!(
            inputs.len() + 1 <= self.params.t,
            "Poseidon: too many inputs for single block ({} > {})",
            inputs.len(),
            self.params.t - 1
        );

        let mut state = vec![Fr::zero(); self.params.t];
        for (i, input) in inputs.iter().enumerate() {
            state[i + 1] = *input;
        }

        let mut round = 0;

        for _ in 0..(self.params.rf / 2) {
            state = self.full_round(&state, round);
            round += 1;
        }

        for _ in 0..self.params.rp {
            state = self.partial_round(&state, round);
            round += 1;
        }

        for _ in 0..(self.params.rf / 2) {
            state = self.full_round(&state, round);
            round += 1;
        }

        state[0]
    }

    fn full_round(&self, state: &[Fr], round: usize) -> Vec<Fr> {
        let mut new_state = state.to_vec();

        for i in 0..self.params.t {
            new_state[i] += self.params.round_constants[round][i];
        }

        for i in 0..self.params.t {
            new_state[i] = self.sbox(new_state[i]);
        }

        self.apply_mds(&new_state)
    }

    fn partial_round(&self, state: &[Fr], round: usize) -> Vec<Fr> {
        let mut new_state = state.to_vec();

        for i in 0..self.params.t {
            new_state[i] += self.params.round_constants[round][i];
        }

        new_state[0] = self.sbox(new_state[0]);

        self.apply_mds(&new_state)
    }

    fn sbox(&self, x: Fr) -> Fr {
        let x2 = x * x;
        let x4 = x2 * x2;
        x4 * x
    }

    fn apply_mds(&self, state: &[Fr]) -> Vec<Fr> {
        let mut result = vec![Fr::zero(); self.params.t];

        for i in 0..self.params.t {
            for j in 0..self.params.t {
                result[i] += self.params.mds_matrix[i][j] * state[j];
            }
        }

        result
    }
}

/// Convert string/bytes to field element via SHA-256.
pub fn string_to_field(s: &str) -> Fr {
    use sha2::{Digest, Sha256};

    let hash = Sha256::digest(s.as_bytes());
    Fr::from_be_bytes_mod_order(&hash[..32])
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_poseidon_basic() {
        let hasher = Poseidon::new();
        let a = Fr::from(1u64);
        let b = Fr::from(2u64);
        let result = hasher.hash_two(&a, &b);

        let result2 = hasher.hash_two(&a, &b);
        assert_eq!(result, result2);

        let c = Fr::from(3u64);
        let result3 = hasher.hash_two(&a, &c);
        assert_ne!(result, result3);
    }

    #[test]
    fn test_string_to_field() {
        let f1 = string_to_field("email");
        let f2 = string_to_field("ssn");
        assert_ne!(f1, f2);

        let f3 = string_to_field("email");
        assert_eq!(f1, f3);
    }
}