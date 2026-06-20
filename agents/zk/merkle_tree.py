"""Poseidon Merkle tree builder matching apx-zk circuit semantics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .entity_commitment import field_to_decimal
from .poseidon_client import PoseidonClient, get_poseidon_client

MERKLE_DEPTH = 8
BATCH_SIZE = 4
LEAF_DOMAIN = 1
PADDING_CONST = 0xDEADBEEF


@dataclass(frozen=True)
class MerkleInclusionPath:
    path_elements: List[int]
    path_indices: List[int]

    def as_decimal_lists(self) -> Tuple[List[str], List[str]]:
        return (
            [field_to_decimal(value) for value in self.path_elements],
            [field_to_decimal(value) for value in self.path_indices],
        )


@dataclass(frozen=True)
class PoseidonMerkleTree:
    root: int
    raw_leaves: List[int]
    domain_leaves: List[int]
    levels: List[List[int]]
    paths: List[MerkleInclusionPath]

    @property
    def root_decimal(self) -> str:
        return field_to_decimal(self.root)


def _build_levels(
    domain_leaves: List[int],
    *,
    poseidon: PoseidonClient,
    padding_sentinel: int,
) -> List[List[int]]:
    levels: List[List[int]] = [domain_leaves]
    while len(levels[-1]) > 1:
        current = levels[-1]
        next_level: List[int] = []
        for index in range(0, len(current), 2):
            left = current[index]
            right = current[index + 1] if index + 1 < len(current) else padding_sentinel
            next_level.append(poseidon.hash_two(left, right))
        levels.append(next_level)
    return levels


def build_poseidon_merkle_tree(
    raw_commitments: List[int],
    *,
    client: Optional[PoseidonClient] = None,
) -> PoseidonMerkleTree:
    if not raw_commitments:
        raise ValueError("Cannot build Merkle tree without commitments")

    poseidon = client or get_poseidon_client()
    padding_sentinel = poseidon.hash_two(LEAF_DOMAIN, PADDING_CONST)
    domain_leaves = [
        poseidon.hash_two(LEAF_DOMAIN, commitment) for commitment in raw_commitments
    ]
    levels = _build_levels(domain_leaves, poseidon=poseidon, padding_sentinel=padding_sentinel)

    current_root = levels[-1][0]
    for _ in range(len(levels) - 1, MERKLE_DEPTH):
        current_root = poseidon.hash_two(current_root, padding_sentinel)

    paths: List[MerkleInclusionPath] = []
    for leaf_index in range(len(domain_leaves)):
        path_elements = [0] * MERKLE_DEPTH
        path_indices = [0] * MERKLE_DEPTH
        index = leaf_index
        for level_index in range(len(levels) - 1):
            level = levels[level_index]
            sibling_index = index ^ 1
            if sibling_index < len(level):
                sibling = level[sibling_index]
            else:
                sibling = padding_sentinel
            path_elements[level_index] = sibling
            path_indices[level_index] = index % 2
            index //= 2
        for level_index in range(len(levels) - 1, MERKLE_DEPTH):
            path_elements[level_index] = padding_sentinel
            path_indices[level_index] = 0
        paths.append(MerkleInclusionPath(path_elements=path_elements, path_indices=path_indices))

    return PoseidonMerkleTree(
        root=current_root,
        raw_leaves=list(raw_commitments),
        domain_leaves=domain_leaves,
        levels=levels,
        paths=paths,
    )


def build_batch_merkle_witness(
    tree: PoseidonMerkleTree,
    entity_count: int,
) -> dict:
    """Build batch-merkle circuit inputs for up to BATCH_SIZE entities."""
    if entity_count <= 0 or entity_count > BATCH_SIZE:
        raise ValueError(f"batch-merkle supports 1..{BATCH_SIZE} entities, got {entity_count}")

    leaves = [tree.raw_leaves[0]] * BATCH_SIZE
    path_elements = [[field_to_decimal(0)] * MERKLE_DEPTH for _ in range(BATCH_SIZE)]
    path_indices = [[field_to_decimal(0)] * MERKLE_DEPTH for _ in range(BATCH_SIZE)]

    for index in range(entity_count):
        leaves[index] = tree.raw_leaves[index]
        elements, indices = tree.paths[index].as_decimal_lists()
        path_elements[index] = elements
        path_indices[index] = indices

    fallback_elements, fallback_indices = tree.paths[0].as_decimal_lists()
    for index in range(entity_count, BATCH_SIZE):
        path_elements[index] = list(fallback_elements)
        path_indices[index] = list(fallback_indices)

    return {
        "merkle_root": tree.root_decimal,
        "entity_count": entity_count,
        "leaves": [field_to_decimal(value) for value in leaves],
        "path_elements": path_elements,
        "path_indices": path_indices,
    }