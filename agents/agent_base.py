"""
APX v1 — Shared agent runtime wiring (Phase 2)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

from .artifact_provider import FileArtifactProvider
from .audit_logger import AuditLogger
from .capability_checker import CapabilityChecker

if TYPE_CHECKING:
    from .runtime import APXRuntime


DEFAULT_AGENT_CAPABILITIES = {
    "APX-AGENT-001": ["read_specification", "write_artifact", "execute_agent"],
    "APX-AGENT-002": ["read_specification", "write_artifact", "execute_agent"],
    "APX-AGENT-003": ["read_specification", "write_artifact", "execute_agent", "verify_attestation"],
}


def init_agent_context(
    agent_id: str,
    agent_name: str,
    audit_filename: str,
    base_path: Optional[Path] = None,
    runtime: Optional["APXRuntime"] = None,
) -> Dict[str, Any]:
    """Initialize shared Phase 2 agent context (provider, capabilities, audit)."""
    if runtime is not None:
        root = runtime.base_path
        provider = runtime.provider
        capability_checker = runtime.capability_checker
        governance = runtime.governance
    else:
        root = Path(base_path) if base_path else Path(__file__).parent.parent
        provider = FileArtifactProvider(base_path=root)
        capability_checker = CapabilityChecker()
        governance = None
        for cap in DEFAULT_AGENT_CAPABILITIES.get(agent_id, []):
            capability_checker.grant_capability(agent_id, cap)

    audit_logger = AuditLogger(log_path=root / "managed" / "audit" / audit_filename)
    audit_logger.log_event(
        event_type="agent_initialized",
        data={
            "agent_id": agent_id,
            "agent_name": agent_name,
            "base_path": str(root),
            "runtime_attached": runtime is not None,
        },
    )

    return {
        "base_path": root,
        "provider": provider,
        "capability_checker": capability_checker,
        "audit_logger": audit_logger,
        "governance": governance,
        "runtime": runtime,
    }


def register_loaded_specs(governance: Any, specs: Dict[str, Dict[str, Any]]) -> None:
    if governance is None:
        return
    for spec in specs.values():
        governance.register_specification(spec)