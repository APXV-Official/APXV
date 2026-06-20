"""Tests for Phase 4 entity ZK bridge and dual proof bundles."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.zk.bridge import EntityZKBridge
from agents.zk.bundle import build_dual_proof_bundle, build_governance_proof_bundle
from agents.zk.entity_commitment import create_entity_commitments, string_to_field
from agents.zk.merkle_tree import build_poseidon_merkle_tree
from agents.zk.poseidon_client import PoseidonClient
from tests.test_pipeline import SAMPLE_INPUT, run_pipeline


@pytest.fixture(scope="module")
def poseidon_client() -> PoseidonClient:
    client = PoseidonClient(base_path=ROOT)
    client._run("hash-two", "1", "2")
    return client


def test_poseidon_hash_two_matches_rust_vectors(poseidon_client: PoseidonClient):
    result = poseidon_client.hash_two(1, 2)
    expected = 7853200120776062878684798364095072458815029376092732009249414926327459813530
    assert result == expected


def test_entity_commitments_are_deterministic(poseidon_client: PoseidonClient):
    entities = [
        {"type": "email", "value": "john.doe@example.com", "start": 8},
        {"type": "phone", "value": "(555) 123-4567", "start": 40},
    ]
    first = create_entity_commitments(entities, poseidon=poseidon_client)
    second = create_entity_commitments(entities, poseidon=poseidon_client)
    assert [item.commitment for item in first] == [item.commitment for item in second]
    assert first[0].entity_type == "email"
    assert "value" not in first[0].as_public_dict()


def test_merkle_tree_root_non_zero(poseidon_client: PoseidonClient):
    commitments = [string_to_field("a"), string_to_field("b"), string_to_field("c")]
    tree = build_poseidon_merkle_tree(commitments, client=poseidon_client)
    assert int(tree.root_decimal) > 0
    assert len(tree.paths) == 3


def test_prepare_entity_inputs_from_attested(poseidon_client: PoseidonClient):
    attested = run_pipeline(input_text=SAMPLE_INPUT)
    bridge = EntityZKBridge(base_path=ROOT)
    bridge.poseidon = poseidon_client
    prepared = bridge.prepare_entity_inputs(attested)
    assert prepared["entity_count"] >= 1
    assert "redaction-v1" in prepared
    assert "core-redaction" in prepared
    assert prepared["redaction-v1"]["original_data_hash"]
    assert prepared["redaction-v1"]["redacted_data_hash"]
    assert len(prepared["redaction-v1"]["leaf_commitments"]) == 8


def test_dual_proof_bundle_structure():
    attested = {
        "zk_proof_redaction": {"proof_hex": "abc", "vk_hex": "def"},
        "zk_proof_rule_binding": {"proof_hex": "abc", "vk_hex": "def"},
        "zk_proof_pipeline": {"proof_hex": "abc", "vk_hex": "def"},
        "entity_proofs": {
            "proofs": {"redaction_v1": {"proof_hex": "aaa", "verification_result": True}},
            "metadata": {"entity_count": 1},
        },
    }
    dual = build_dual_proof_bundle(attested)
    assert "governance_proofs" in dual
    assert "entity_proofs" in dual
    assert "redaction" in dual["governance_proofs"]["proofs"]
    assert "redaction_v1" in dual["entity_proofs"]["proofs"]


@pytest.mark.skipif(
    not (ROOT / "rust" / "Cargo.toml").exists(),
    reason="Rust workspace not available",
)
def test_entity_zk_prove_redaction_v1_round_trip(poseidon_client: PoseidonClient):
    attested = run_pipeline(input_text=SAMPLE_INPUT)
    bridge = EntityZKBridge(base_path=ROOT)
    bridge.poseidon = poseidon_client
    prepared = bridge.prepare_entity_inputs(attested)

    from scripts.setup_entity_zk import ensure_entity_zk_setup

    ensure_entity_zk_setup(base_path=ROOT)

    proof = bridge.prove_circuit("redaction-v1", prepared["redaction-v1"])
    assert proof.get("verification_result") is True, proof
    assert proof.get("proof_hex")
    assert proof.get("vk_hex")


@pytest.mark.skipif(
    not (ROOT / "rust" / "Cargo.toml").exists(),
    reason="Rust workspace not available",
)
def test_full_dual_attest_and_verify():
    result = subprocess.run(
        [sys.executable, "-m", "scripts.run_apx", "--attest"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert result.returncode == 0, result.stderr[-1000:]

    verify = subprocess.run(
        [sys.executable, "-m", "scripts.verify_attestation", "--real-zk"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert verify.returncode == 0, verify.stdout + verify.stderr
    assert "ENTITY GROTH16 PROOFS INDEPENDENTLY VERIFIED" in verify.stdout

    artifacts = sorted((ROOT / "managed" / "artifacts").glob("attested_result_pipeline_with_zk_*.json"))
    assert artifacts
    wrapped = json.loads(artifacts[-1].read_text(encoding="utf-8"))
    attested = wrapped.get("artifact", wrapped)
    assert "governance_proofs" in attested
    assert "entity_proofs" in attested
    assert attested["entity_proofs"]["metadata"]["entity_count"] >= 1