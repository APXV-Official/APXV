"""Tests for APXV Pipeline Spec v0.1 — validate, dump, load, round-trip."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.pipeline_spec import (
    PipelineSpecError,
    documents_semantically_equal,
    dump_pipeline,
    load_pipeline_text,
    parse_uses,
    validate_pipeline_document,
)

VALID_DOC = {
    "apiVersion": "apxv.pipeline/v0.1",
    "kind": "Pipeline",
    "id": "apxv-pipeline-reference-linear",
    "name": "Reference linear composition",
    "version": "0.1.0",
    "description": "Example",
    "defaults": {"attest": False, "on_step_failure": "stop"},
    "steps": [
        {"id": "redact", "name": "Rule-governed redaction", "uses": "agent:APXV-AGENT-001"},
        {"id": "orchestrate", "name": "Workflow orchestration", "uses": "agent:APXV-AGENT-002"},
        {"id": "decide", "name": "Attestation coordination", "uses": "agent:APXV-AGENT-003"},
    ],
}


def test_validate_accepts_valid_document():
    result = validate_pipeline_document(VALID_DOC)
    assert result.ok, result.errors
    assert result.document["id"] == "apxv-pipeline-reference-linear"
    assert len(result.document["steps"]) == 3


def test_validate_rejects_bad_api_version():
    bad = {**VALID_DOC, "apiVersion": "wrong"}
    result = validate_pipeline_document(bad)
    assert not result.ok
    assert any("apiVersion" in e for e in result.errors)


def test_validate_rejects_empty_steps():
    bad = {**VALID_DOC, "steps": []}
    result = validate_pipeline_document(bad)
    assert not result.ok


def test_validate_rejects_duplicate_step_ids():
    bad = {
        **VALID_DOC,
        "steps": [
            {"id": "a", "name": "A", "uses": "agent:APXV-AGENT-001"},
            {"id": "a", "name": "B", "uses": "agent:APXV-AGENT-002"},
        ],
    }
    result = validate_pipeline_document(bad)
    assert not result.ok
    assert any("duplicate" in e for e in result.errors)


def test_validate_rejects_secret_like_config():
    bad = {
        **VALID_DOC,
        "steps": [
            {
                "id": "redact",
                "name": "R",
                "uses": "agent:APXV-AGENT-001",
                "config": {"api_key": "should-not-appear"},
            }
        ],
    }
    result = validate_pipeline_document(bad)
    assert not result.ok
    assert any("secret" in e.lower() or "api_key" in e for e in result.errors)


def test_parse_uses_agent_pack_attest():
    assert parse_uses("agent:APXV-AGENT-001")["kind"] == "agent"
    assert parse_uses("pack:apxv-pack-reference-redaction")["kind"] == "pack"
    assert parse_uses("apxv:attest")["kind"] == "attest"
    with pytest.raises(PipelineSpecError):
        parse_uses("unknown:foo")


def test_json_round_trip():
    result = validate_pipeline_document(VALID_DOC)
    doc = result.document
    text = dump_pipeline(doc, fmt="json")
    loaded = load_pipeline_text(text, fmt="json")
    again = validate_pipeline_document(loaded)
    assert again.ok
    assert documents_semantically_equal(doc, again.document)


def test_yaml_round_trip():
    result = validate_pipeline_document(VALID_DOC)
    doc = result.document
    text = dump_pipeline(doc, fmt="yaml")
    loaded = load_pipeline_text(text, fmt="yaml")
    again = validate_pipeline_document(loaded)
    assert again.ok, again.errors
    assert documents_semantically_equal(doc, again.document)


def test_example_pipeline_files_validate():
    examples = ROOT / "examples" / "pipelines"
    files = list(examples.glob("*.yaml"))
    assert files, "expected example pipeline YAML files"
    for path in files:
        text = path.read_text(encoding="utf-8")
        loaded = load_pipeline_text(text, fmt="yaml")
        result = validate_pipeline_document(loaded)
        assert result.ok, f"{path.name}: {result.errors}"
