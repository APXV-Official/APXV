"""Poseidon entity commitments for ZK entity proofs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .poseidon_client import hash_fields

BN254_MODULUS = 21888242871839275222246405745257275088548364400416034343698204186575808495617
POSITION_SENTINEL = (1 << 53) - 1


def string_to_field(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(digest, "big") % BN254_MODULUS


def field_to_decimal(value: int) -> str:
    return str(value % BN254_MODULUS)


@dataclass(frozen=True)
class EntityCommitment:
    entity_type: str
    position: int
    commitment: int
    sha256_hash: str
    leaf_index: int

    def as_public_dict(self) -> Dict[str, Any]:
        return {
            "type": self.entity_type,
            "position": self.position,
            "commitment": field_to_decimal(self.commitment),
            "sha256_hash": self.sha256_hash,
            "leaf_index": self.leaf_index,
        }


def _normalize_entity(entity: Dict[str, Any]) -> tuple[str, str, int]:
    entity_type = str(entity.get("type", "unknown")).lower()
    value = str(entity.get("value", ""))
    position = entity.get("start", entity.get("position", -1))
    if not isinstance(position, int):
        position = -1
    if position < 0:
        position = POSITION_SENTINEL
    return entity_type, value, position


def create_entity_commitment(
    entity: Dict[str, Any],
    *,
    leaf_index: int = 0,
    poseidon: Optional[Any] = None,
) -> EntityCommitment:
    entity_type, value, position = _normalize_entity(entity)
    type_field = string_to_field(entity_type)
    value_field = string_to_field(value)
    position_field = position % BN254_MODULUS
    commitment = hash_fields(
        [type_field, value_field, position_field],
        client=poseidon,
    )
    value_digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    sha256_hash = hashlib.sha256(
        f"{entity_type}|{value_digest}|{position}".encode("utf-8")
    ).hexdigest()
    return EntityCommitment(
        entity_type=entity_type,
        position=position,
        commitment=commitment,
        sha256_hash=sha256_hash,
        leaf_index=leaf_index,
    )


def create_entity_commitments(
    entities: List[Dict[str, Any]],
    *,
    poseidon: Optional[Any] = None,
) -> List[EntityCommitment]:
    return [
        create_entity_commitment(entity, leaf_index=index, poseidon=poseidon)
        for index, entity in enumerate(entities)
    ]


def entities_digest(commitments: List[EntityCommitment], *, poseidon: Optional[Any] = None) -> int:
    """Poseidon sequential digest of the first 8 leaf commitments (pad with zero)."""
    leaves = [0] * 8
    for index, commitment in enumerate(commitments[:8]):
        leaves[index] = commitment.commitment
    return hash_fields(leaves, client=poseidon)