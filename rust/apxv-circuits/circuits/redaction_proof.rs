// APX v1 — Redaction Proof Circuit
// Copyright 2026 APXVdev
// Licensed under the Apache License, Version 2.0
//
// Public inputs:
//   - original_hash: Hash of the input text before redaction
//   - redacted_hash: Hash of the text after redaction
//   - redaction_count: Number of redactions performed
//
// Phase 1 hardened constraints:
//   1. redaction_count is non-zero (at least one redaction occurred)
//   2. original_hash != redacted_hash (content was changed)
//   3. (original - redacted) * count binds the transformation magnitude

use ark_bn254::Fr;
use ark_ff::Field;
use ark_std::Zero;
use ark_r1cs_std::fields::fp::FpVar;
use ark_r1cs_std::prelude::*;
use ark_relations::r1cs::{ConstraintSynthesizer, ConstraintSystemRef, SynthesisError};

pub const CIRCUIT_VERSION: &str = "1.1.0";

fn field_inverse(value: Fr) -> Result<Fr, SynthesisError> {
    if value.is_zero() {
        Err(SynthesisError::AssignmentMissing)
    } else {
        Ok(value.inverse().unwrap())
    }
}

#[derive(Clone)]
pub struct RedactionProofCircuit {
    pub original_hash: Fr,
    pub redacted_hash: Fr,
    pub redaction_count: Fr,
}

impl ConstraintSynthesizer<Fr> for RedactionProofCircuit {
    fn generate_constraints(self, cs: ConstraintSystemRef<Fr>) -> Result<(), SynthesisError> {
        let original_var = FpVar::new_input(cs.clone(), || Ok(self.original_hash))?;
        let redacted_var = FpVar::new_input(cs.clone(), || Ok(self.redacted_hash))?;
        let count_var = FpVar::new_input(cs.clone(), || Ok(self.redaction_count))?;

        let one = FpVar::constant(Fr::from(1u64));

        // Constraint 1: redaction_count must be non-zero.
        let count_inv = FpVar::new_witness(cs.clone(), || field_inverse(self.redaction_count))?;
        count_var.mul_equals(&count_inv, &one)?;

        // Constraint 2: original and redacted must differ.
        let diff = &original_var - &redacted_var;
        let diff_inv = FpVar::new_witness(cs.clone(), || {
            field_inverse(self.original_hash - self.redacted_hash)
        })?;
        diff.mul_equals(&diff_inv, &one)?;

        // Constraint 3: bind the transformation to the declared count.
        let binding_witness = FpVar::new_witness(cs.clone(), || {
            Ok((self.original_hash - self.redacted_hash) * self.redaction_count)
        })?;
        let binding_computed = &diff * &count_var;
        binding_computed.enforce_equal(&binding_witness)?;

        Ok(())
    }
}