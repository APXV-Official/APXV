"""
APXV — Hello Agent Example

A minimal custom governed agent that:
- Uses APXRuntime for capabilities, audit, and artifacts
- Processes input text
- Writes a structured artifact
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agents.agent_base import init_agent_context
from agents.runtime import APXRuntime


class HelloAgent:
    """Minimal example agent for building on APXV."""

    def __init__(self, runtime: APXRuntime | None = None):
        self.agent_id = "APXV-AGENT-LLM-001"
        self.agent_name = "HelloAgent"
        self.runtime = runtime or APXRuntime()
        ctx = init_agent_context(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            audit_filename="hello_agent_audit.log",
            runtime=self.runtime,
        )
        self.provider = ctx["provider"]
        self.audit_logger = ctx["audit_logger"]
        self.capability_checker = ctx["capability_checker"]

    def run(self, message: str) -> dict:
        self.capability_checker.require_capability(self.agent_id, "execute_agent")
        self.capability_checker.require_capability(self.agent_id, "write_artifact")

        result = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "input_message": message,
            "output_message": f"Hello from APXV — received {len(message)} characters",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "governed": True,
        }

        write_meta = self.provider.write_artifact(artifact=result, name="hello_agent_output")
        self.audit_logger.log_event(
            event_type="hello_agent_executed",
            data={"artifact_hash": write_meta.get("content_hash"), "input_length": len(message)},
        )

        return {"result": result, "artifact": write_meta}


def main() -> int:
    message = " ".join(sys.argv[1:]) or "world"
    agent = HelloAgent()
    output = agent.run(message)
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())