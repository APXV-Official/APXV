"""Tests for pluggable LLM backends."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.llm_backend import SimulatedLLMBackend
from agents.llm_reasoner import LLMReasoner


def test_simulated_backend_returns_response():
    backend = SimulatedLLMBackend()
    result = backend.complete("review this document please")
    assert result.text
    assert result.latency_ms >= 0
    assert result.model == "simulated"


def test_llm_reasoner_with_simulated_backend(tmp_path):
    (tmp_path / "managed" / "rules").mkdir(parents=True)
    (tmp_path / "managed" / "workflows").mkdir(parents=True)
    (tmp_path / "managed" / "knowledge").mkdir(parents=True)
    for spec, name in (
        ("rules", "rule1.md"),
        ("workflows", "workflow1.md"),
        ("knowledge", "knowledge1.md"),
    ):
        src = ROOT / "managed" / spec / name
        (tmp_path / "managed" / spec / name).write_text(
            src.read_text(encoding="utf-8"), encoding="utf-8"
        )

    from scripts.setup_first_run import run_setup

    run_setup(tmp_path, setup_zk=False)

    from agents.runtime import APXRuntime

    runtime = APXRuntime(base_path=tmp_path)
    agent = LLMReasoner(
        runtime=runtime,
        backend=SimulatedLLMBackend(),
    )
    output = agent.execute({"prompt": "review this for release"})
    assert output.agent_id == "APXV-AGENT-LLM-001"
    assert output.decision in ("APPROVED", "REJECTED", "REVIEW_REQUIRED")
    assert output.reasoning_summary