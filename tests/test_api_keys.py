"""Tests for API key management."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.auth import APIKeyAuth


def test_create_and_list_api_keys(tmp_path):
    config = tmp_path / "api_keys.json"
    auth = APIKeyAuth(config)

    raw = auth.create_key("test-app", description="unit test")
    assert raw
    assert auth.validate(raw) is True
    assert auth.validate("wrong") is False

    listed = auth.list_keys()
    assert len(listed) == 1
    assert listed[0]["id"] == "test-app"
    assert "key_hash" not in listed[0]


def test_duplicate_key_id_rejected(tmp_path):
    config = tmp_path / "api_keys.json"
    auth = APIKeyAuth(config)
    auth.create_key("dup")
    with pytest.raises(ValueError):
        auth.create_key("dup")