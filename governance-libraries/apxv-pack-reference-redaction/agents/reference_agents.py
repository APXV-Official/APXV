"""Thin bindings to APXV1 core agents — no duplicate pipeline logic."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agents.agent1 import RuleGovernedRedactor
from agents.agent2 import WorkflowOrchestrator
from agents.agent3 import AttestationCoordinator

PACK_AGENT_IDS = (
    "APX-AGENT-001",
    "APX-AGENT-002",
    "APX-AGENT-003",
)

__all__ = [
    "PACK_AGENT_IDS",
    "RuleGovernedRedactor",
    "WorkflowOrchestrator",
    "AttestationCoordinator",
]