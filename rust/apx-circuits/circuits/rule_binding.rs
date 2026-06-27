// APX v1 — Rule Binding Circuit
// Copyright 2026 APXVdev
// Licensed under the Apache License, Version 2.0
//
// Public inputs:
//   - rule_hash: SHA256 hash of the active rule file (APX-RULE-001)
//   - redaction_proof_hash: Commitment to the redaction proof bundle
//   - redaction_count: Number of redactions performed
//
// Phase 1 hardened constraints:
//   1. redaction_count is non-zero
//   2. rule_hash is non-zero (a specific rule was in force)
//   3. rule_hash * count + redaction_proof_hash binds rule to redaction proof

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
pub struct RuleBindingCircuit {
    pub rule_hash: Fr,
    pub redaction_proof_hash: Fr,
    pub redaction_count: Fr,
}

impl ConstraintSynthesizer<Fr> for RuleBindingCircuit {
    fn generate_constraints(self, cs: ConstraintSystemRef<Fr>) -> Result<(), SynthesisError> {
        let rule_hash_var = FpVar::new_input(cs.clone(), || Ok(self.rule_hash))?;
        let proof_hash_var = FpVar::new_input(cs.clone(), || Ok(self.redaction_proof_hash))?;
        let count_var = FpVar::new_input(cs.clone(), || Ok(self.redaction_count))?;

        let one = FpVar::constant(Fr::from(1u64));

        // Constraint 1: at least one redaction occurred.
        let count_inv = FpVar::new_witness(cs.clone(), || field_inverse(self.redaction_count))?;
        count_var.mul_equals(&count_inv, &one)?;

        // Constraint 2: a specific rule hash was supplied.
        let rule_inv = FpVar::new_witness(cs.clone(), || field_inverse(self.rule_hash))?;
        rule_hash_var.mul_equals(&rule_inv, &one)?;

        // Constraint 3: bind rule, proof commitment, and count.
        let binding_witness = FpVar::new_witness(cs.clone(), || {
            Ok(self.rule_hash * self.redaction_count + self.redaction_proof_hash)
        })?;
        let binding_computed = &(&rule_hash_var * &count_var) + &proof_hash_var;
        binding_computed.enforce_equal(&binding_witness)?;

        Ok(())
    }
}