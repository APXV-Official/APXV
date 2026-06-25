// Copyright 2026 APXV Official
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

//! Cross-verification tests for BN254 Poseidon hashes.

#[cfg(test)]
mod poseidon_crosscheck {
    use crate::poseidon::Poseidon;
    use ark_bn254::Fr;
    use std::str::FromStr;

    fn fr_from_decimal(s: &str) -> Fr {
        Fr::from_str(s).expect("valid decimal field element")
    }

    #[test]
    fn test_poseidon_hash_0_0() {
        let hasher = Poseidon::new();
        let left = Fr::from(0u64);
        let right = Fr::from(0u64);
        let result = hasher.hash_two(&left, &right);

        let expected = fr_from_decimal(
            "14744269619966411208579211824598458697587494354926760081771325075741142829156",
        );

        assert_eq!(result, expected, "Poseidon hash(0, 0) mismatch!");
    }

    #[test]
    fn test_poseidon_hash_1_1() {
        let hasher = Poseidon::new();
        let left = Fr::from(1u64);
        let right = Fr::from(1u64);
        let result = hasher.hash_two(&left, &right);

        let expected = fr_from_decimal(
            "217234377348884654691879377518794323857294947151490278790710809376325639809",
        );

        assert_eq!(result, expected, "Poseidon hash(1, 1) mismatch!");
    }

    #[test]
    fn test_poseidon_hash_1_2() {
        let hasher = Poseidon::new();
        let left = Fr::from(1u64);
        let right = Fr::from(2u64);
        let result = hasher.hash_two(&left, &right);

        let expected = fr_from_decimal(
            "7853200120776062878684798364095072458815029376092732009249414926327459813530",
        );

        assert_eq!(result, expected, "Poseidon hash(1, 2) mismatch!");
    }

    #[test]
    fn test_poseidon_hash_12345_67890() {
        let hasher = Poseidon::new();
        let left = Fr::from(12345u64);
        let right = Fr::from(67890u64);
        let result = hasher.hash_two(&left, &right);

        let expected = fr_from_decimal(
            "11344094074881186137859743404234365978119253787583526441303892667757095072923",
        );

        assert_eq!(result, expected, "Poseidon hash(12345, 67890) mismatch!");
    }

    #[test]
    fn test_poseidon_hash_large() {
        let hasher = Poseidon::new();
        let left = fr_from_decimal(
            "100720434726375746010458024839911619878118703404436202866098422983289408962287",
        );
        let right = fr_from_decimal(
            "91817263436861762419153095791742601532679023100463714610640035083621647694526",
        );
        let result = hasher.hash_two(&left, &right);

        let expected = fr_from_decimal(
            "11569418402987103885719114898798216021119774940051492076077484795699935592850",
        );

        assert_eq!(result, expected, "Poseidon hash(large, large) mismatch!");
    }
}