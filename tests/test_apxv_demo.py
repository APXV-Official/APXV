"""Smoke tests for apxv_demo entrypoint."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize(
    "pack",
    ["reference", "document", "ai"],
)
def test_pack_demo_paths_exist(pack: str):
    from scripts.apxv_demo import _pack_demo_path

    assert _pack_demo_path(pack).is_file()


def test_resolve_pack_runs_reference():
    from scripts.apxv_demo import resolve_pack_runs

    runs = resolve_pack_runs("reference")
    assert len(runs) == 1
    assert runs[0][0] == "reference"


def test_resolve_pack_runs_all():
    from scripts.apxv_demo import resolve_pack_runs

    runs = resolve_pack_runs("all")
    assert [name for name, _ in runs] == ["reference", "document", "ai"]
    assert all(path.is_file() for _name, path in runs)


def test_apxv_demo_module_imports():
    from scripts import apxv_demo

    assert callable(apxv_demo.main)
    assert "all" in apxv_demo.PACK_CHOICES


def test_onboard_pack_resolution_matches_apxv_demo():
    from scripts import apxv_demo, onboard

    for pack in ("reference", "document", "ai", "all"):
        assert onboard.resolve_pack_runs(pack) == apxv_demo.resolve_pack_runs(pack)