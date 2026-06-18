"""
APX v1 Agents Package

This package contains the three small agents for the APX v1 minimal reference implementation.

Agents in this package are designed to:
- Read rules, workflows, and knowledge from the managed/ markdown files at runtime.
- Follow the defined workflows precisely.
- Produce outputs that can be turned into governed artifacts.
- Support cryptographic attestation in later integration steps.

All code here is original work for APX v1.
"""

from .agent1 import RuleGovernedRedactor
from .agent2 import WorkflowOrchestrator
from .agent3 import AttestationCoordinator
from .artifact_provider import MinimalArtifactProvider, SqliteArtifactProvider
from .runtime import APXRuntime

__all__ = [
    "RuleGovernedRedactor",
    "WorkflowOrchestrator",
    "AttestationCoordinator",
    "MinimalArtifactProvider",
    "SqliteArtifactProvider",
    "APXRuntime",
]
