"""Bridge attested pipeline output to apxv-zk entity Groth16 proofs."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.entity_zk_manifest import attach_entity_key_metadata

from .entity_commitment import (
    create_entity_commitments,
    entities_digest,
    field_to_decimal,
)
from .compliance_policy import build_compliance_witness, resolve_compliance_policy_id
from .merkle_tree import (
    BATCH_SIZE,
    build_batch_merkle_witness,
    build_merkle_inclusion_witness,
    build_poseidon_merkle_tree,
)
from .poseidon_client import PoseidonClient, build_apx_zk_command

ENTITY_VERSION = "1.1.0"
MAX_MERKLE_INCLUSION_PROOFS = 8
PRIMARY_ENTITY_CIRCUITS = (
    "redaction-v1",
    "core-redaction",
    "batch-merkle",
    "merkle-inclusion",
    "compliance",
)


class EntityZKBridge:
    def __init__(self, base_path: Optional[Path] = None) -> None:
        self.base_path = base_path or Path(__file__).parent.parent.parent
        self.rust_dir = self.base_path / "rust"
        self.crate_dir = self.rust_dir / "apxv-zk"
        self.manifest = self.rust_dir / "Cargo.toml"
        self.poseidon = PoseidonClient(base_path=self.base_path)

    def _extract_entities(self, attested: Dict[str, Any]) -> List[Dict[str, Any]]:
        proposed = attested.get("proposed_artifact", {})
        output = proposed.get("output", {})
        entities = output.get("entities", [])
        if isinstance(entities, list) and entities:
            return entities

        voice_session = attested.get("voice_session", {})
        if isinstance(voice_session, dict):
            voice_entities = voice_session.get("entities", [])
            if isinstance(voice_entities, list) and voice_entities:
                return voice_entities

        redactions = output.get("redactions_applied", [])
        rebuilt: List[Dict[str, Any]] = []
        for item in redactions:
            value = item.get("original", item.get("value"))
            if value is None and "count" in item:
                continue
            rebuilt.append(
                {
                    "type": item.get("category", item.get("type", "unknown")).lower(),
                    "value": value or "",
                    "start": item.get("position", item.get("start", -1)),
                }
            )
        return rebuilt

    def prepare_entity_inputs(self, attested: Dict[str, Any]) -> Dict[str, Any]:
        proposed = attested.get("proposed_artifact", {})
        output = proposed.get("output", {})
        input_block = proposed.get("input", {})

        entities = self._extract_entities(attested)
        if not entities:
            raise ValueError("No entities found in attested artifact — cannot build entity proofs")

        commitments = create_entity_commitments(entities, poseidon=self.poseidon)
        raw_values = [commitment.commitment for commitment in commitments]
        tree = build_poseidon_merkle_tree(raw_values, client=self.poseidon)
        digest = entities_digest(commitments, poseidon=self.poseidon)

        leaf_commitments = [0] * 8
        for index, commitment in enumerate(commitments[:8]):
            leaf_commitments[index] = commitment.commitment

        original_hash = input_block.get("original_hash", "")
        redacted_hash = input_block.get("post_redaction_hash", "")
        entity_count = len(commitments)

        redaction_v1 = {
            "merkle_root": tree.root_decimal,
            "entity_count": entity_count,
            "entities_digest": field_to_decimal(digest),
            "original_data_hash": original_hash,
            "redacted_data_hash": redacted_hash,
            "leaf_commitments": [field_to_decimal(value) for value in leaf_commitments],
        }
        core_redaction = {
            "merkle_root": tree.root_decimal,
            "entity_count": entity_count,
            "original_data_hash": original_hash,
            "redacted_data_hash": redacted_hash,
        }

        prepared: Dict[str, Any] = {
            "entity_count": entity_count,
            "merkle_root": tree.root_decimal,
            "entities_digest": field_to_decimal(digest),
            "commitments": [commitment.as_public_dict() for commitment in commitments],
            "redaction-v1": redaction_v1,
            "core-redaction": core_redaction,
        }

        if 1 <= entity_count <= BATCH_SIZE:
            prepared["batch-merkle"] = build_batch_merkle_witness(tree, entity_count)

        inclusion_count = min(entity_count, MAX_MERKLE_INCLUSION_PROOFS)
        if inclusion_count >= 1:
            prepared["merkle-inclusion"] = [
                build_merkle_inclusion_witness(tree, index)
                for index in range(inclusion_count)
            ]

        policy_id = resolve_compliance_policy_id(attested)
        if policy_id is not None:
            prepared["compliance"] = build_compliance_witness(
                entity_count=entity_count,
                policy_id=policy_id,
                original_hash=original_hash,
                redacted_hash=redacted_hash,
            )
            prepared["compliance_policy_id"] = policy_id

        return prepared

    def prove_circuit(self, circuit: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmp:
            inputs_path = Path(tmp) / f"{circuit}_inputs.json"
            inputs_path.write_text(json.dumps(inputs, indent=2), encoding="utf-8")
            cmd, cwd = build_apx_zk_command(
                self.base_path,
                "prove", circuit, "--inputs", str(inputs_path),
            )
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode != 0:
                return {
                    "status": "proof_failed",
                    "circuit": circuit,
                    "error": result.stderr[-800:],
                }

            proof_path = inputs_path.with_name(f"{circuit}_proof.json")
            if not proof_path.exists():
                return {"status": "proof_output_missing", "circuit": circuit}

            proof_bundle = json.loads(proof_path.read_text(encoding="utf-8"))
            try:
                attach_entity_key_metadata(proof_bundle, circuit, base_path=self.base_path)
            except Exception:
                pass
            return proof_bundle

    def generate_entity_proofs(self, attested: Dict[str, Any]) -> Dict[str, Any]:
        from scripts.setup_entity_zk import ensure_entity_zk_setup

        ensure_entity_zk_setup(base_path=self.base_path)

        prepared = self.prepare_entity_inputs(attested)
        circuits_to_run: List[str] = ["redaction-v1", "core-redaction"]
        if "batch-merkle" in prepared:
            circuits_to_run.append("batch-merkle")

        voice_inputs = (
            attested.get("voice_session", {}).get("voice_redaction_inputs")
            if isinstance(attested.get("voice_session"), dict)
            else None
        )
        if isinstance(voice_inputs, dict) and voice_inputs:
            circuits_to_run.append("voice-redaction")

        inclusion_witnesses = prepared.get("merkle-inclusion", [])
        if isinstance(inclusion_witnesses, list):
            for index in range(len(inclusion_witnesses)):
                circuits_to_run.append(f"merkle-inclusion:{index}")

        if "compliance" in prepared:
            circuits_to_run.append("compliance")

        proofs: Dict[str, Any] = {}
        for circuit in ["redaction-v1", "core-redaction"]:
            proof = self.prove_circuit(circuit, prepared[circuit])
            proofs[circuit.replace("-", "_")] = proof

        if "batch-merkle" in prepared:
            proof = self.prove_circuit("batch-merkle", prepared["batch-merkle"])
            proofs["batch_merkle"] = proof

        if isinstance(inclusion_witnesses, list):
            for index, witness in enumerate(inclusion_witnesses):
                proof = self.prove_circuit("merkle-inclusion", witness)
                proofs[f"merkle_inclusion_{index}"] = proof

        if "compliance" in prepared:
            proof = self.prove_circuit("compliance", prepared["compliance"])
            proofs["compliance"] = proof

        if isinstance(voice_inputs, dict) and voice_inputs:
            proof = self.prove_circuit("voice-redaction", voice_inputs)
            proofs["voice_redaction"] = proof

        metadata = {
            "version": ENTITY_VERSION,
            "entity_count": prepared["entity_count"],
            "merkle_root": prepared["merkle_root"],
            "entities_digest": prepared["entities_digest"],
            "commitments": prepared["commitments"],
            "circuits": circuits_to_run,
        }
        if isinstance(inclusion_witnesses, list) and inclusion_witnesses:
            metadata["merkle_inclusion_count"] = len(inclusion_witnesses)
        if prepared.get("compliance_policy_id") is not None:
            metadata["compliance_policy_id"] = prepared["compliance_policy_id"]
        if voice_inputs:
            metadata["voice_redaction"] = True

        return {
            "track": "entity",
            "version": ENTITY_VERSION,
            "metadata": metadata,
            "proofs": proofs,
        }


def generate_entity_proofs(
    attested: Dict[str, Any],
    base_path: Optional[Path] = None,
) -> Dict[str, Any]:
    return EntityZKBridge(base_path=base_path).generate_entity_proofs(attested)