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

//! APXV1 entity Groth16 zero-knowledge proof system (BN254).

use ark_bn254::Fr;

pub mod poseidon;
mod poseidon_constants;
pub mod poseidon_gadget;
pub mod circuits;
pub mod keygen;

#[cfg(test)]
mod poseidon_tests;

/// BN254 scalar field element used throughout APX ZK circuits.
pub type APXField = Fr;