"""Tests for ZK key manifest and VK integrity checks."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts.zk_manifest import (
    CIRCUIT_VERSION,
    expected_vk_hash,
    load_manifest,
    rebuild_manifest,
)


def test_manifest_exists_after_setup():
    manifest = load_manifest(ROOT)
    assert manifest.get("circuit_version") == CIRCUIT_VERSION
    assert "redaction" in manifest.get("circuits", {})


def test_expected_vk_hash_for_redaction():
    rebuild_manifest(base_path=ROOT)
    vk_hash = expected_vk_hash("redaction", base_path=ROOT)
    assert vk_hash is not None
    assert len(vk_hash) == 64