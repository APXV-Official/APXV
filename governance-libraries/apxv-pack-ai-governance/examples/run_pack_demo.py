"""AI Governance Pack — redaction + LLM review demo."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def _load_governance_agents():
    mod_path = Path(__file__).resolve().parents[1] / "agents" / "governance_agents.py"
    spec = importlib.util.spec_from_file_location("pack_governance_agents", mod_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load pack agents from {mod_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_gov = _load_governance_agents()
run_governed_ai_pipeline = _gov.run_governed_ai_pipeline
SAMPLE_INPUT = _gov.SAMPLE_INPUT


def main() -> int:
    input_text = SAMPLE_INPUT
    if len(sys.argv) > 1:
        input_text = Path(sys.argv[1]).read_text(encoding="utf-8")

    result = run_governed_ai_pipeline(input_text)
    status = result.get("final_status")
    output = result.get("proposed_artifact", {}).get("output", {})
    redactions = output.get("total_redactions", 0)
    policy_id = output.get("compliance_policy_id")
    llm_decision = result.get("llm_decision")

    print(
        "Pack demo complete: "
        f"final_status={status}, llm_decision={llm_decision}, "
        f"total_redactions={redactions}, compliance_policy_id={policy_id}"
    )

    if status != "ATTESTED":
        return 1
    if redactions < 1:
        return 1
    if policy_id != 4:
        return 1
    if llm_decision not in ("APPROVED", "REVIEW_REQUIRED", "REJECTED"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())