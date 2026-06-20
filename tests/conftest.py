"""Pytest hooks and fixtures."""

from __future__ import annotations

from pathlib import Path


def pytest_ignore_collect(collection_path: Path, config):
    """Skip legacy reference trees without hard-coding vendor names in config."""
    name = collection_path.name
    if name.endswith("SDK v1.0.0") or name.endswith("-proof-system"):
        return True
    if name == "legacy":
        return True
    return None