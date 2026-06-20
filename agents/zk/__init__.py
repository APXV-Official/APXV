"""APX entity ZK orchestration bridge (Phase 4)."""

from .bridge import EntityZKBridge, generate_entity_proofs
from .bundle import build_dual_proof_bundle

__all__ = [
    "EntityZKBridge",
    "generate_entity_proofs",
    "build_dual_proof_bundle",
]