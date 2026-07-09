"""Agent ID normalization — APX-AGENT ↔ APXV-AGENT dual-prefix (DP-1 Option A)."""

from __future__ import annotations

from typing import List

_AGENT_PREFIX_LEGACY = "APX-AGENT-"
_AGENT_PREFIX_CANONICAL = "APXV-AGENT-"


def normalize_agent_id(agent_id: str) -> str:
    """Return canonical APXV-AGENT-* identifier."""
    if agent_id.startswith(_AGENT_PREFIX_LEGACY):
        return _AGENT_PREFIX_CANONICAL + agent_id[len(_AGENT_PREFIX_LEGACY) :]
    return agent_id


def agent_id_variants(agent_id: str) -> List[str]:
    """Return lookup variants for capability and registry resolution."""
    canonical = normalize_agent_id(agent_id)
    legacy = agent_id
    if canonical.startswith(_AGENT_PREFIX_CANONICAL):
        legacy = _AGENT_PREFIX_LEGACY + canonical[len(_AGENT_PREFIX_CANONICAL) :]

    variants: List[str] = []
    for candidate in (agent_id, canonical, legacy):
        if candidate and candidate not in variants:
            variants.append(candidate)
    return variants