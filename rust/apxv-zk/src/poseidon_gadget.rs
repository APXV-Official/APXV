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

//! Poseidon hash gadget — R1CS constraint-generating version for BN254.

use ark_bn254::Fr;
use ark_ff::Zero;
use ark_r1cs_std::fields::fp::FpVar;
use ark_r1cs_std::fields::FieldVar;

use crate::poseidon_constants;

// ──────────────────────────────────────────────────────────────────────────────
// Public gadget
// ──────────────────────────────────────────────────────────────────────────────

pub struct PoseidonGadget {
    round_constants: Vec<Vec<Fr>>,
    mds_matrix: Vec<Vec<Fr>>,
}

impl PoseidonGadget {
    /// Create a new gadget instance.  Loads the same round constants and MDS
    /// matrix used by the native `Poseidon` struct so the two are always in sync.
    pub fn new() -> Self {
        Self {
            round_constants: poseidon_constants::get_round_constants(),
            mds_matrix: poseidon_constants::get_mds_matrix(),
        }
    }

    /// Constrained Poseidon hash of two R1CS field variables.
    ///
    /// Returns a new `FpVar<Fr>` whose value equals Poseidon(left, right) **and**
    /// whose relationship to `left` / `right` is fully enforced by R1CS
    /// multiplication constraints.  It is therefore impossible for a malicious
    /// prover to set the returned value to anything other than the correct hash.
    pub fn hash_two(&self, left: &FpVar<Fr>, right: &FpVar<Fr>) -> FpVar<Fr> {
        // Initialise the t=3 state as [capacity=0, left, right]
        let mut state = vec![
            FpVar::constant(Fr::zero()),
            left.clone(),
            right.clone(),
        ];

        let mut round = 0usize;

        // First half of full rounds (rf/2 = 4)
        for _ in 0..4 {
            state = self.full_round(state, round);
            round += 1;
        }

        // Partial rounds (rp = 57)
        for _ in 0..57 {
            state = self.partial_round(state, round);
            round += 1;
        }

        // Second half of full rounds (rf/2 = 4)
        for _ in 0..4 {
            state = self.full_round(state, round);
            round += 1;
        }

        // Output is state[0]
        state.into_iter().next().unwrap()
    }
}

// ──────────────────────────────────────────────────────────────────────────────
// Internal round functions
// ──────────────────────────────────────────────────────────────────────────────

impl PoseidonGadget {
    /// Full round: add round constants, then apply the x^5 S-box to **all**
    /// t=3 elements, then multiply by the MDS matrix.
    fn full_round(&self, state: Vec<FpVar<Fr>>, round: usize) -> Vec<FpVar<Fr>> {
        let rc = &self.round_constants[round];
        let after_sbox: Vec<FpVar<Fr>> = state
            .into_iter()
            .enumerate()
            .map(|(i, s)| {
                let s_plus_rc = s + FpVar::constant(rc[i]);
                Self::sbox(s_plus_rc)
            })
            .collect();
        self.apply_mds(&after_sbox)
    }

    /// Partial round: add round constants, apply x^5 S-box to the **first**
    /// element only, then multiply by the MDS matrix.
    fn partial_round(&self, state: Vec<FpVar<Fr>>, round: usize) -> Vec<FpVar<Fr>> {
        let rc = &self.round_constants[round];
        // Add round constants to every element
        let mut with_rc: Vec<FpVar<Fr>> = state
            .into_iter()
            .enumerate()
            .map(|(i, s)| s + FpVar::constant(rc[i]))
            .collect();
        // S-box only on element 0
        let first = with_rc.remove(0);
        with_rc.insert(0, Self::sbox(first));
        self.apply_mds(&with_rc)
    }

    /// x^5 S-box — generates exactly 3 R1CS multiplication constraints:
    ///   x2 = x  * x      (constraint 1)
    ///   x4 = x2 * x2     (constraint 2)
    ///   x5 = x4 * x      (constraint 3)
    ///
    /// Multiplying by a `FpVar::Constant` (round constants, MDS entries) is
    /// "free" in R1CS — it just scales a linear combination without a new gate.
    fn sbox(x: FpVar<Fr>) -> FpVar<Fr> {
        let x2 = x.clone() * x.clone(); // x^2
        let x4 = x2.clone() * x2;       // x^4
        x4 * x                           // x^5
    }

    /// MDS linear layer.  Because every coefficient `mds_matrix[i][j]` is a
    /// field constant, no new multiplication gates are needed here — each term
    /// `state[j] * constant` is just a scaled linear combination.
    fn apply_mds(&self, state: &[FpVar<Fr>]) -> Vec<FpVar<Fr>> {
        let t = state.len();
        let mut result = Vec::with_capacity(t);
        for i in 0..t {
            let mut row = FpVar::constant(Fr::zero());
            for j in 0..t {
                let coeff = FpVar::constant(self.mds_matrix[i][j]);
                row = row + state[j].clone() * coeff;
            }
            result.push(row);
        }
        result
    }
}

// ──────────────────────────────────────────────────────────────────────────────
// Cross-check tests — verify the gadget produces the same values as the native
// Poseidon when given honest witnesses (i.e., same hash function, correct params)
// ──────────────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use ark_ff::One;
    use ark_r1cs_std::alloc::AllocVar;
    use ark_r1cs_std::R1CSVar;
    use ark_relations::r1cs::ConstraintSystem;
    use crate::poseidon::Poseidon;

    /// Helper: allocate a constant FpVar so we can call hash_two in a CS
    fn fp_const(cs: &ark_relations::r1cs::ConstraintSystemRef<Fr>, v: Fr) -> FpVar<Fr> {
        FpVar::new_input(cs.clone(), || Ok(v)).unwrap()
    }

    #[test]
    fn gadget_matches_native_hash() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        let native = Poseidon::new();
        let gadget = PoseidonGadget::new();

        let a = Fr::from(42u64);
        let b = Fr::from(99u64);

        let a_var = fp_const(&cs, a);
        let b_var = fp_const(&cs, b);

        let native_out = native.hash_two(&a, &b);
        let gadget_out = gadget.hash_two(&a_var, &b_var);

        assert_eq!(
            gadget_out.value().unwrap(),
            native_out,
            "Gadget output must match native Poseidon output"
        );
        assert!(cs.is_satisfied().unwrap(), "Constraint system should be satisfied");
    }

    #[test]
    fn gadget_matches_native_with_zero() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        let native = Poseidon::new();
        let gadget = PoseidonGadget::new();

        let a = Fr::from(1000u64);
        let b = Fr::zero();

        let a_var = fp_const(&cs, a);
        let b_var = fp_const(&cs, b);

        let native_out = native.hash_two(&a, &b);
        let gadget_out = gadget.hash_two(&a_var, &b_var);

        assert_eq!(gadget_out.value().unwrap(), native_out);
        assert!(cs.is_satisfied().unwrap());
    }

    #[test]
    fn gadget_matches_native_with_one() {
        let cs = ConstraintSystem::<Fr>::new_ref();
        let native = Poseidon::new();
        let gadget = PoseidonGadget::new();

        let a = Fr::one();
        let b = Fr::one();

        let a_var = fp_const(&cs, a);
        let b_var = fp_const(&cs, b);

        let native_out = native.hash_two(&a, &b);
        let gadget_out = gadget.hash_two(&a_var, &b_var);

        assert_eq!(gadget_out.value().unwrap(), native_out);
        assert!(cs.is_satisfied().unwrap());
    }
}
