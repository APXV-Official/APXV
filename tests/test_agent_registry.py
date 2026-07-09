"""Tests for Agent Registry (PR-1c)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.agent_registry import agents_for_pack, get_agent, list_agents
from agents.runtime import APXRuntime

from tests.helpers import seed_governance_libraries, seed_test_instance


@pytest.fixture
def registry_env(tmp_path):
    seed_governance_libraries(tmp_path)
    seed_test_instance(tmp_path)
    runtime = APXRuntime(base_path=tmp_path)
    return tmp_path, runtime


def test_list_agents_includes_core_pipeline(registry_env):
    base, runtime = registry_env
    agents = list_agents(base, runtime=runtime)
    ids = {agent["id"] for agent in agents}
    assert "APXV-AGENT-001" in ids
    assert "APXV-AGENT-002" in ids
    assert "APXV-AGENT-003" in ids

    agent1 = next(a for a in agents if a["id"] == "APXV-AGENT-001")
    assert agent1["name"] == "RuleGovernedRedactor"
    assert agent1["kind"] == "core"
    assert "execute_agent" in agent1["capabilities"]
    assert len(agent1["packs"]) >= 3


def test_get_agent_llm_in_ai_pack(registry_env):
    base, runtime = registry_env
    agent = get_agent(base, "APXV-AGENT-LLM-001", runtime=runtime)
    assert agent is not None
    assert agent["name"] == "LLMReasoner"
    assert "apxv-pack-ai-governance" in agent["packs"]


def test_agents_for_pack_reference_chain_order(registry_env):
    base, runtime = registry_env
    result = agents_for_pack(base, "apxv-pack-reference-redaction", runtime=runtime)
    assert result["pack_id"] == "apxv-pack-reference-redaction"
    chain = result["agents"]
    assert len(chain) == 3
    assert [item["id"] for item in chain] == [
        "APXV-AGENT-001",
        "APXV-AGENT-002",
        "APXV-AGENT-003",
    ]
    assert chain[0]["chain_index"] == 0
    assert chain[2]["chain_index"] == 2
    assert chain[0]["declared_module"] == "agents.agent1"


def test_agents_for_pack_ai_includes_llm(registry_env):
    base, runtime = registry_env
    result = agents_for_pack(base, "apxv-pack-ai-governance", runtime=runtime)
    ids = [item["id"] for item in result["agents"]]
    assert ids == [
        "APXV-AGENT-001",
        "APXV-AGENT-002",
        "APXV-AGENT-003",
        "APXV-AGENT-LLM-001",
    ]
    llm = result["agents"][-1]
    assert llm["declared_type"] == "agentic"
    assert llm["declared_module"] == "agents.llm_reasoner"


def test_agents_for_pack_document_discovers_module(registry_env):
    base, runtime = registry_env
    result = agents_for_pack(base, "apxv-pack-document-processing", runtime=runtime)
    discovered = {item["stem"] for item in result["discovered_modules"]}
    assert "document_agents" in discovered


def test_get_agent_unknown_returns_none(registry_env):
    base, runtime = registry_env
    assert get_agent(base, "APXV-AGENT-DOES-NOT-EXIST", runtime=runtime) is None


def test_custom_pack_agent_in_registry(registry_env):
    base, runtime = registry_env
    agent = get_agent(base, "APXV-AGENT-CUSTOM-001", runtime=runtime)
    assert agent is not None
    assert "apxv-pack-test-ui" in agent["packs"]