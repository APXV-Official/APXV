"""
APXV Agents Package

This package contains the three small agents for the APXV minimal reference implementation.

Agents in this package are designed to:
- Read rules, workflows, and knowledge from the managed/ markdown files at runtime.
- Follow the defined workflows precisely.
- Produce outputs that can be turned into governed artifacts.
- Support cryptographic attestation in later integration steps.

All code here is original work for APXV.
"""

from .agent1 import RuleGovernedRedactor
from .agent2 import WorkflowOrchestrator
from .agent3 import AttestationCoordinator
from .artifact_provider import MinimalArtifactProvider, SqliteArtifactProvider
from .runtime import APXVRuntime, APXRuntime

__all__ = [
    "RuleGovernedRedactor",
    "WorkflowOrchestrator",
    "AttestationCoordinator",
    "MinimalArtifactProvider",
    "SqliteArtifactProvider",
    "APXVRuntime",
    "APXRuntime",
]
