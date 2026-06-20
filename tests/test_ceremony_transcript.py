"""Tests for ZK ceremony transcript (Tier A/B)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts.ceremony_transcript import (
    build_transcript,
    transcript_content_hash,
    verify_transcript,
    write_transcript,
)
from scripts.export_verifier_bundle import export_verifier_bundle


def test_build_transcript_matches_manifests():
    doc = build_transcript(ROOT, sign=False)
    assert doc["transcript_version"] == "1.0.0"
    assert "circuits" in doc["governance"]
    assert doc["governance"]["circuits"]["redaction"]["vk_hash"]
    assert doc["entity"]["circuits"]["voice-redaction"]["vk_hash"]
    assert doc["content_hash"] == transcript_content_hash(doc)


def test_write_and_verify_transcript(tmp_path):
    for spec in ("rules", "workflows", "knowledge"):
        (tmp_path / "managed" / spec).mkdir(parents=True, exist_ok=True)
    (tmp_path / "rust" / "apx-circuits" / "keys").mkdir(parents=True)
    (tmp_path / "rust" / "apx-zk" / "keys").mkdir(parents=True)
    import shutil

    shutil.copytree(ROOT / "rust" / "apx-circuits" / "keys", tmp_path / "rust" / "apx-circuits" / "keys", dirs_exist_ok=True)
    shutil.copytree(ROOT / "rust" / "apx-zk" / "keys", tmp_path / "rust" / "apx-zk" / "keys", dirs_exist_ok=True)

    from scripts.setup_first_run import run_setup

    run_setup(tmp_path, setup_zk=False)

    path = write_transcript(tmp_path, sign=False, ceremony_tier="A")
    assert path.exists()
    result = verify_transcript(tmp_path)
    assert result["valid"] is True


def test_verify_fails_on_tamper(tmp_path):
    for spec in ("rules", "workflows", "knowledge"):
        (tmp_path / "managed" / spec).mkdir(parents=True, exist_ok=True)
    (tmp_path / "rust" / "apx-circuits" / "keys").mkdir(parents=True)
    (tmp_path / "rust" / "apx-zk" / "keys").mkdir(parents=True)
    import shutil

    shutil.copytree(ROOT / "rust" / "apx-circuits" / "keys", tmp_path / "rust" / "apx-circuits" / "keys", dirs_exist_ok=True)
    shutil.copytree(ROOT / "rust" / "apx-zk" / "keys", tmp_path / "rust" / "apx-zk" / "keys", dirs_exist_ok=True)
    from scripts.setup_first_run import run_setup

    run_setup(tmp_path, setup_zk=False)
    write_transcript(tmp_path, sign=False)

    path = tmp_path / "managed" / "config" / "ceremony-transcript.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["operator_note"] = "tampered"
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    result = verify_transcript(tmp_path)
    assert result["valid"] is False
    assert any("content_hash" in i for i in result["issues"])


def test_export_verifier_bundle_no_pk(tmp_path):
    export_verifier_bundle(tmp_path / "bundle", base_path=ROOT)
    bundle = tmp_path / "bundle"
    assert not any(bundle.rglob("*.pk"))
    assert (bundle / "governance" / "manifest.json").exists()
    assert (bundle / "entity" / "entity-manifest.json").exists()
    assert len(list((bundle / "entity").glob("*.vk"))) == 8