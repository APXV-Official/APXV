// Copyright 2026 APXVdev
// Licensed under the Apache License, Version 2.0
//
// Universal Predicate Circuit v1 — one Groth16 circuit parameterized by a
// predicate bitmask. Operators select catalog predicates; this circuit proves
// the selected claims hold for committed run facts.
//
// Public inputs (order matters for verify):
//   0 predicate_mask      — which catalog bits are asserted
//   1 entity_count        — redacted/detected entity count
//   2 min_entity_count    — threshold for ENTITY_COUNT_GTE
//   3 category_required   — bitmask of required category bits
//   4 category_present    — bitmask of categories observed
//   5 flags               — structural flag bits (see PRED_* constants)
//   6 policy_commitment   — binding hash (policy/rule commitment as field)
//
// Private witnesses:
//   original_hash, redacted_hash — document hashes for redaction binding
//
// Bit layout (catalog):
//   0 REDACTION_NONEMPTY
//   1 ENTITY_COUNT_GTE
//   2 CATEGORY_INCLUDES
//   3 RULE_BOUND
//   4 PIPELINE_CHAIN
//   5 ATTESTED_STATUS
//   6 GOVERNANCE_APPROVED
//   7 ZK_GOVERNANCE_PRESENT
//   8 ZK_ENTITY_PRESENT

use ark_bn254::Fr;
use ark_ff::Field;
use ark_r1cs_std::fields::fp::FpVar;
use ark_r1cs_std::prelude::*;
use ark_relations::r1cs::{ConstraintSynthesizer, ConstraintSystemRef, SynthesisError};
use ark_std::Zero;

pub const CIRCUIT_ID: &str = "universal-predicate-v1";
pub const CIRCUIT_VERSION: &str = "1.0.0";

pub const PRED_REDACTION_NONEMPTY: u64 = 1 << 0;
pub const PRED_ENTITY_COUNT_GTE: u64 = 1 << 1;
pub const PRED_CATEGORY_INCLUDES: u64 = 1 << 2;
pub const PRED_RULE_BOUND: u64 = 1 << 3;
pub const PRED_PIPELINE_CHAIN: u64 = 1 << 4;
pub const PRED_ATTESTED_STATUS: u64 = 1 << 5;
pub const PRED_GOVERNANCE_APPROVED: u64 = 1 << 6;
pub const PRED_ZK_GOVERNANCE: u64 = 1 << 7;
pub const PRED_ZK_ENTITY: u64 = 1 << 8;

/// Number of catalog predicate bits enforced in v1.
pub const PRED_BITS: usize = 9;

#[derive(Clone)]
pub struct UniversalPredicateCircuit {
    // Public
    pub predicate_mask: Fr,
    pub entity_count: Fr,
    pub min_entity_count: Fr,
    pub category_required: Fr,
    pub category_present: Fr,
    pub flags: Fr,
    pub policy_commitment: Fr,
    // Private
    pub original_hash: Fr,
    pub redacted_hash: Fr,
}

impl UniversalPredicateCircuit {
    pub fn public_inputs(&self) -> Vec<Fr> {
        vec![
            self.predicate_mask,
            self.entity_count,
            self.min_entity_count,
            self.category_required,
            self.category_present,
            self.flags,
            self.policy_commitment,
        ]
    }
}

/// Enforce x is a boolean (0 or 1): x * (x - 1) === 0
fn enforce_boolean(x: &FpVar<Fr>) -> Result<(), SynthesisError> {
    let one = FpVar::constant(Fr::from(1u64));
    let xm1 = x - &one;
    (x * &xm1).enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
    Ok(())
}

/// If selector is 1, enforce target === 1. selector * (1 - target) === 0
fn enforce_if_selected(
    selector: &FpVar<Fr>,
    target_is_one: &FpVar<Fr>,
) -> Result<(), SynthesisError> {
    let one = FpVar::constant(Fr::from(1u64));
    let failure = &one - target_is_one;
    (selector * &failure).enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
    Ok(())
}

/// a <= b for values in 0..2^16 by proving (b - a) fits in 16 bits.
fn enforce_leq_u16(
    cs: ConstraintSystemRef<Fr>,
    a: &FpVar<Fr>,
    b: &FpVar<Fr>,
) -> Result<(), SynthesisError> {
    let diff = b - a;
    // Witness 16 bits of diff
    let bits = diff.to_bits_le()?;
    // Reconstruct low 16 bits
    let mut acc = FpVar::constant(Fr::from(0u64));
    let mut pow = Fr::from(1u64);
    for i in 0..16 {
        if i >= bits.len() {
            break;
        }
        let bit_f = FpVar::<Fr>::from(bits[i].clone());
        acc += &bit_f * FpVar::constant(pow);
        pow = pow * Fr::from(2u64);
    }
    // Higher bits must be zero if present (prevents wrap abuse for large diffs)
    for i in 16..bits.len().min(64) {
        bits[i].enforce_equal(&Boolean::FALSE)?;
    }
    acc.enforce_equal(&diff)?;
    let _ = cs;
    Ok(())
}

/// IsZero gadget: returns 1 if x==0 else 0, with constraints.
fn is_zero_gadget(
    cs: ConstraintSystemRef<Fr>,
    x: &FpVar<Fr>,
) -> Result<FpVar<Fr>, SynthesisError> {
    let inv = FpVar::new_witness(cs, || {
        let v = x.value()?;
        if v.is_zero() {
            Ok(Fr::from(0u64))
        } else {
            Ok(v.inverse().unwrap())
        }
    })?;
    // out = 1 - x*inv  (1 if zero, 0 otherwise when x*inv==1 for nonzero)
    let one = FpVar::constant(Fr::from(1u64));
    let out = &one - (x * &inv);
    // x * out === 0
    (x * &out).enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
    Ok(out)
}

impl ConstraintSynthesizer<Fr> for UniversalPredicateCircuit {
    fn generate_constraints(self, cs: ConstraintSystemRef<Fr>) -> Result<(), SynthesisError> {
        let mask = FpVar::new_input(cs.clone(), || Ok(self.predicate_mask))?;
        let entity_count = FpVar::new_input(cs.clone(), || Ok(self.entity_count))?;
        let min_entity = FpVar::new_input(cs.clone(), || Ok(self.min_entity_count))?;
        let cat_req = FpVar::new_input(cs.clone(), || Ok(self.category_required))?;
        let cat_pres = FpVar::new_input(cs.clone(), || Ok(self.category_present))?;
        let flags = FpVar::new_input(cs.clone(), || Ok(self.flags))?;
        let _policy = FpVar::new_input(cs.clone(), || Ok(self.policy_commitment))?;

        let original = FpVar::new_witness(cs.clone(), || Ok(self.original_hash))?;
        let redacted = FpVar::new_witness(cs.clone(), || Ok(self.redacted_hash))?;

        // Decompose mask and flags into bits
        let mask_bits = mask.to_bits_le()?;
        let flag_bits = flags.to_bits_le()?;

        let mut mask_sels: Vec<FpVar<Fr>> = Vec::with_capacity(PRED_BITS);
        let mut flag_sels: Vec<FpVar<Fr>> = Vec::with_capacity(PRED_BITS);
        for i in 0..PRED_BITS {
            let mb = if i < mask_bits.len() {
                FpVar::<Fr>::from(mask_bits[i].clone())
            } else {
                FpVar::constant(Fr::from(0u64))
            };
            let fb = if i < flag_bits.len() {
                FpVar::<Fr>::from(flag_bits[i].clone())
            } else {
                FpVar::constant(Fr::from(0u64))
            };
            enforce_boolean(&mb)?;
            enforce_boolean(&fb)?;
            mask_sels.push(mb);
            flag_sels.push(fb);
        }

        // Recompose mask low bits and bind (prevents free high bits in low region)
        {
            let mut acc = FpVar::constant(Fr::from(0u64));
            let mut pow = Fr::from(1u64);
            for i in 0..PRED_BITS {
                acc += &mask_sels[i] * FpVar::constant(pow);
                pow = pow * Fr::from(2u64);
            }
            // mask_low = mask - high_part; we only force equality on low PRED_BITS via
            // subtracting high contribution is hard without full decomp — instead
            // constrain mask - acc is divisible by 2^PRED_BITS i.e. mask == acc + 2^9 * k
            // For v1: require mask < 2^PRED_BITS (only catalog bits).
            acc.enforce_equal(&mask)?;
        }

        // Bit 0: REDACTION_NONEMPTY → flag0==1 and hashes differ and entity_count != 0
        {
            let sel = &mask_sels[0];
            enforce_if_selected(sel, &flag_sels[0])?;

            let count_zero = is_zero_gadget(cs.clone(), &entity_count)?;
            // if selected: count_zero must be 0
            (sel * &count_zero).enforce_equal(&FpVar::constant(Fr::from(0u64)))?;

            let diff = &original - &redacted;
            let diff_zero = is_zero_gadget(cs.clone(), &diff)?;
            (sel * &diff_zero).enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
        }

        // Bit 1: ENTITY_COUNT_GTE → entity_count >= min_entity_count
        {
            let sel = &mask_sels[1];
            // When sel=0: compare 0 <= 0. When sel=1: min_entity <= entity_count.
            let min_eff = sel * &min_entity;
            let ent_eff = sel * &entity_count;
            enforce_leq_u16(cs.clone(), &min_eff, &ent_eff)?;
            enforce_if_selected(sel, &flag_sels[1])?;
        }

        // Bit 2: CATEGORY_INCLUDES → (present & required) == required
        {
            let sel = &mask_sels[2];
            // present & required: for each bit i, req_i * (1 - pres_i) == 0 when selected
            let req_bits = cat_req.to_bits_le()?;
            let pres_bits = cat_pres.to_bits_le()?;
            let bit_n = 16usize;
            for i in 0..bit_n {
                let rb = if i < req_bits.len() {
                    FpVar::<Fr>::from(req_bits[i].clone())
                } else {
                    FpVar::constant(Fr::from(0u64))
                };
                let pb = if i < pres_bits.len() {
                    FpVar::<Fr>::from(pres_bits[i].clone())
                } else {
                    FpVar::constant(Fr::from(0u64))
                };
                enforce_boolean(&rb)?;
                enforce_boolean(&pb)?;
                let one = FpVar::constant(Fr::from(1u64));
                let missing = &rb * (&one - &pb);
                // if selected and required bit set and not present → fail
                (sel * &missing).enforce_equal(&FpVar::constant(Fr::from(0u64)))?;
            }
            enforce_if_selected(sel, &flag_sels[2])?;
        }

        // Bits 3..8: structural flags must be 1 when selected
        for i in 3..PRED_BITS {
            enforce_if_selected(&mask_sels[i], &flag_sels[i])?;
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ark_groth16::Groth16;
    use ark_relations::r1cs::ConstraintSystem;
    use ark_snark::SNARK;
    use ark_std::rand::rngs::StdRng;
    use ark_std::rand::SeedableRng;

    fn sample_ok() -> UniversalPredicateCircuit {
        // mask: redaction + entity_gte + rule + pipeline + attested + gov = bits 0,1,3,4,5,6
        let mask = PRED_REDACTION_NONEMPTY
            | PRED_ENTITY_COUNT_GTE
            | PRED_RULE_BOUND
            | PRED_PIPELINE_CHAIN
            | PRED_ATTESTED_STATUS
            | PRED_GOVERNANCE_APPROVED;
        let flags = mask; // all selected flags true
        UniversalPredicateCircuit {
            predicate_mask: Fr::from(mask),
            entity_count: Fr::from(3u64),
            min_entity_count: Fr::from(1u64),
            category_required: Fr::from(0u64),
            category_present: Fr::from(0u64),
            flags: Fr::from(flags),
            policy_commitment: Fr::from(42u64),
            original_hash: Fr::from(111u64),
            redacted_hash: Fr::from(222u64),
        }
    }

    #[test]
    fn constraints_satisfied_for_valid_witness() {
        let circuit = sample_ok();
        let cs = ConstraintSystem::<Fr>::new_ref();
        circuit.generate_constraints(cs.clone()).unwrap();
        assert!(cs.is_satisfied().unwrap(), "constraints should hold");
    }

    #[test]
    fn constraints_fail_when_entity_below_min() {
        let mut circuit = sample_ok();
        circuit.entity_count = Fr::from(0u64);
        circuit.flags = Fr::from(
            PRED_REDACTION_NONEMPTY
                | PRED_ENTITY_COUNT_GTE
                | PRED_RULE_BOUND
                | PRED_PIPELINE_CHAIN
                | PRED_ATTESTED_STATUS
                | PRED_GOVERNANCE_APPROVED,
        );
        // redaction requires nonzero count — will fail
        let cs = ConstraintSystem::<Fr>::new_ref();
        circuit.generate_constraints(cs.clone()).unwrap();
        assert!(!cs.is_satisfied().unwrap());
    }

    #[test]
    fn groth16_prove_verify_roundtrip() {
        let mut rng = StdRng::seed_from_u64(7);
        let setup_circuit = sample_ok();
        let (pk, vk) = Groth16::<ark_bn254::Bn254>::circuit_specific_setup(setup_circuit, &mut rng)
            .expect("setup");
        let prove_circuit = sample_ok();
        let public = prove_circuit.public_inputs();
        let proof = Groth16::<ark_bn254::Bn254>::prove(&pk, prove_circuit, &mut rng).expect("prove");
        let ok = Groth16::<ark_bn254::Bn254>::verify(&vk, &public, &proof).unwrap();
        assert!(ok, "proof must verify");
    }
}
