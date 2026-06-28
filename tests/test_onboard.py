"""Smoke tests for onboarding entrypoint."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_pack_demo_path_exists():
    demo = (
        ROOT
        / "governance-libraries"
        / "apxv-pack-reference-redaction"
        / "examples"
        / "run_pack_demo.py"
    )
    assert demo.is_file()


def test_onboard_module_imports():
    from scripts import onboard

    assert callable(onboard.main)
    assert "document" in onboard.PACK_CHOICES


def test_onboard_document_pack_demo_exists():
    from scripts.onboard import _pack_demo_path

    assert _pack_demo_path("document").is_file()
    assert _pack_demo_path("ai").is_file()