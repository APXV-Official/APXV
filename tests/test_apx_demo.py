"""Smoke tests for apx_demo entrypoint."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize(
    "pack",
    ["reference", "document", "ai"],
)
def test_pack_demo_paths_exist(pack: str):
    from scripts.apx_demo import _pack_demo_path

    assert _pack_demo_path(pack).is_file()


def test_resolve_pack_runs_reference():
    from scripts.apx_demo import resolve_pack_runs

    runs = resolve_pack_runs("reference")
    assert len(runs) == 1
    assert runs[0][0] == "reference"


def test_resolve_pack_runs_all():
    from scripts.apx_demo import resolve_pack_runs

    runs = resolve_pack_runs("all")
    assert [name for name, _ in runs] == ["reference", "document", "ai"]
    assert all(path.is_file() for _name, path in runs)


def test_apx_demo_module_imports():
    from scripts import apx_demo

    assert callable(apx_demo.main)
    assert "all" in apx_demo.PACK_CHOICES


def test_onboard_pack_resolution_matches_apx_demo():
    from scripts import apx_demo, onboard

    for pack in ("reference", "document", "ai", "all"):
        assert onboard.resolve_pack_runs(pack) == apx_demo.resolve_pack_runs(pack)