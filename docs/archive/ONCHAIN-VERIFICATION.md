# APX v1 — On-Chain Verification Guidance

**Status:** Future Capability (Not Yet Implemented)

## Overview

APX v1 is designed with the **potential** for on-chain verification in mind, but this capability has not been implemented yet.

The system can, in principle, support verification of Groth16 proofs and artifact chains on public blockchains or through lightweight WASM clients. This would enable new use cases such as:

- Supply chain provenance with on-chain audit trails
- Decentralized governance with verifiable decisions
- Integration with DeFi protocols or DAOs
- Cross-organization trust without a central authority

## Current State

- All core proofs are generated using Groth16 over BN254 (a curve well-supported on Ethereum and other EVM chains).
- Verification keys and proofs are already portable (`proof_hex` + `vk_hex`).
- The existing Rust verifier (`apx-circuits verify`) can serve as a reference implementation.

## Future Implementation Path

When there is clear demand, the following can be developed:

1. **Solidity Verifier Contract** — A smart contract that can verify APX Groth16 proofs on Ethereum or compatible chains.
2. **WASM Verifier** — A lightweight browser or edge-compatible verifier for decentralized applications.
3. **On-Chain Artifact Anchoring** — Optional anchoring of artifact hashes or audit log roots to a blockchain for public verifiability.

## Recommendation

Do not implement on-chain verification until there is:
- A concrete customer or partner use case
- Clear value in moving verification on-chain
- Resources available to maintain and audit smart contracts

Until then, the off-chain verification tools (`apx-verify`, Rust verifier, auditor scripts) provide full trustless verification without the complexity and cost of on-chain components.

---

*This document serves as a placeholder and future roadmap item.*