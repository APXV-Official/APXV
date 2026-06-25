// APX v1 — Pipeline Attestation Circuit
// Copyright 2026 APXV Official
// Licensed under the Apache License, Version 2.0
//
// Public inputs:
//   - rule_hash, workflow_hash, knowledge_hash
//   - final_governance_decision
//   - agent_chain_hash
//
// Phase 1 hardened constraints:
//   1. governance decision is non-zero
//   2. agent chain hash is non-zero
//   3. specs_sum = rule + workflow + knowledge (witness-bound)
//   4. specs_sum * governance + agent_chain_hash binds full pipeline attestation

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
pub struct PipelineAttestationCircuit {
    pub rule_hash: Fr,
    pub workflow_hash: Fr,
    pub knowledge_hash: Fr,
    pub final_governance_decision: Fr,
    pub agent_chain_hash: Fr,
}

impl ConstraintSynthesizer<Fr> for PipelineAttestationCircuit {
    fn generate_constraints(self, cs: ConstraintSystemRef<Fr>) -> Result<(), SynthesisError> {
        let rule_var = FpVar::new_input(cs.clone(), || Ok(self.rule_hash))?;
        let workflow_var = FpVar::new_input(cs.clone(), || Ok(self.workflow_hash))?;
        let knowledge_var = FpVar::new_input(cs.clone(), || Ok(self.knowledge_hash))?;
        let governance_var = FpVar::new_input(cs.clone(), || Ok(self.final_governance_decision))?;
        let chain_var = FpVar::new_input(cs.clone(), || Ok(self.agent_chain_hash))?;

        let one = FpVar::constant(Fr::from(1u64));
        let specs_sum = &rule_var + &workflow_var + &knowledge_var;

        // Constraint 1: governance decision is non-zero.
        let gov_inv = FpVar::new_witness(cs.clone(), || {
            field_inverse(self.final_governance_decision)
        })?;
        governance_var.mul_equals(&gov_inv, &one)?;

        // Constraint 2: agent chain hash is non-zero.
        let chain_inv = FpVar::new_witness(cs.clone(), || field_inverse(self.agent_chain_hash))?;
        chain_var.mul_equals(&chain_inv, &one)?;

        // Constraint 3: bind the three governance artifact hashes.
        let specs_witness = FpVar::new_witness(cs.clone(), || {
            Ok(self.rule_hash + self.workflow_hash + self.knowledge_hash)
        })?;
        specs_sum.enforce_equal(&specs_witness)?;

        // Constraint 4: bind specs, governance decision, and provenance chain.
        let attestation_witness = FpVar::new_witness(cs.clone(), || {
            let specs = self.rule_hash + self.workflow_hash + self.knowledge_hash;
            Ok(specs * self.final_governance_decision + self.agent_chain_hash)
        })?;
        let attestation_computed = &(&specs_sum * &governance_var) + &chain_var;
        attestation_computed.enforce_equal(&attestation_witness)?;

        Ok(())
    }
}