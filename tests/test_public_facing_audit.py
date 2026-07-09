"""Audit promotable tree + desktop payload for internal leaks and v1.3 doc hygiene."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[1]
if (RUNTIME / "ui").is_dir():
    REPO_ROOT = RUNTIME
else:
    REPO_ROOT = RUNTIME.parent
UI_ROOT = REPO_ROOT / "ui"
PAYLOAD = UI_ROOT / "apps" / "desktop" / "runtime-payload"

FORBIDDEN_TRUST = re.compile(r"skip-zk|Seed-Zk|baked keys", re.I)
INTERNAL_LEAK = re.compile(
    r"02_RnD_Lab|RnD_Lab[/\\]|APXV Personal Build|APXV-CONTROL-PLANE-ROADMAP|"
    r"C:\\APXV Official\\APXV Ecosystem",
    re.I,
)
DEPRECATED_BRAND = re.compile(r"APXV Control Plane|control plane", re.I)

PUBLIC_DOC_ROOTS = [
    RUNTIME / "docs",
    RUNTIME / "website",
    RUNTIME / "README.md",
    UI_ROOT / "docs",
    UI_ROOT / "README.md",
    UI_ROOT / "apps" / "web" / "index.html",
    UI_ROOT / "apps" / "web" / "dist" / "index.html",
]

SKIP_PARTS = {"internal", "resume"}
SKIP_FILES = {
    REPO_ROOT / "DEV-QUICKSTART.md",
    REPO_ROOT / "APXV-CONTROL-PLANE-ROADMAP.md",
    REPO_ROOT / "README.md",
    REPO_ROOT / "RENAME-MATRIX.md",
}


def _collect_md_html(roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if root.is_file():
            if root not in SKIP_FILES:
                out.append(root)
        elif root.is_dir():
            for p in root.rglob("*"):
                if not p.is_file() or p.suffix.lower() not in {".md", ".html"}:
                    continue
                if any(part in SKIP_PARTS for part in p.parts):
                    continue
                if p in SKIP_FILES:
                    continue
                out.append(p)
    return sorted(set(out))


PUBLIC_DOCS = _collect_md_html(PUBLIC_DOC_ROOTS)

WEB_UI_ROOTS = [
    UI_ROOT / "apps" / "web" / "src",
    UI_ROOT / "apps" / "web" / "dist" / "assets",
]
WEB_UI_SUFFIXES = {".tsx", ".ts", ".js"}
WEB_UI_SKIP_PARTS = {"e2e", "node_modules", "__tests__"}


def _collect_web_ui_files() -> list[Path]:
    out: list[Path] = []
    for root in WEB_UI_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in WEB_UI_SUFFIXES:
                continue
            if any(part in WEB_UI_SKIP_PARTS for part in path.parts):
                continue
            out.append(path)
    return sorted(set(out))


WEB_UI_FILES = _collect_web_ui_files()


@pytest.mark.parametrize("path", PUBLIC_DOCS, ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_public_docs_no_forbidden_trust_shortcuts(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = FORBIDDEN_TRUST.search(text)
    assert m is None, f"{path}: forbidden {m.group()!r}"


@pytest.mark.parametrize("path", PUBLIC_DOCS, ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_public_docs_no_internal_path_leaks(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = INTERNAL_LEAK.search(text)
    assert m is None, f"{path}: internal leak {m.group()!r}"


@pytest.mark.parametrize("path", PUBLIC_DOCS, ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_public_docs_no_deprecated_control_plane_brand(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = DEPRECATED_BRAND.search(text)
    assert m is None, f"{path}: deprecated brand {m.group()!r}"


@pytest.mark.parametrize("path", WEB_UI_FILES, ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_web_ui_no_forbidden_trust_shortcuts(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = FORBIDDEN_TRUST.search(text)
    assert m is None, f"{path}: forbidden {m.group()!r}"


@pytest.mark.parametrize("path", WEB_UI_FILES, ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_web_ui_no_internal_path_leaks(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = INTERNAL_LEAK.search(text)
    assert m is None, f"{path}: internal leak {m.group()!r}"


@pytest.mark.parametrize("path", WEB_UI_FILES, ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_web_ui_no_deprecated_control_plane_brand(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = DEPRECATED_BRAND.search(text)
    assert m is None, f"{path}: deprecated brand {m.group()!r}"


def test_payload_excludes_internal_and_resume_docs() -> None:
    if not (PAYLOAD / "docs").is_dir():
        pytest.skip("runtime-payload not staged")
    assert not (PAYLOAD / "docs" / "internal").exists()
    assert not (PAYLOAD / "docs" / "resume").exists()


def test_payload_includes_governance_seed_specs() -> None:
    if not PAYLOAD.is_dir():
        pytest.skip("runtime-payload not staged")
    for spec in ("rules/rule1.md", "workflows/workflow1.md", "knowledge/knowledge1.md"):
        assert (PAYLOAD / "managed" / spec).is_file(), spec


def test_payload_includes_sovereign_docs() -> None:
    if not (PAYLOAD / "docs").is_dir():
        pytest.skip("runtime-payload not staged")
    for name in ("SOVEREIGN-SETUP.md", "INSTALL-USER.md"):
        assert (PAYLOAD / "docs" / name).is_file(), name


def test_payload_docs_no_deprecated_brand_or_leaks() -> None:
    payload_docs = PAYLOAD / "docs"
    if not payload_docs.is_dir():
        pytest.skip("runtime-payload not staged")
    for path in payload_docs.rglob("*.md"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern, label in (
            (FORBIDDEN_TRUST, "forbidden trust"),
            (INTERNAL_LEAK, "internal leak"),
            (DEPRECATED_BRAND, "deprecated brand"),
        ):
            match = pattern.search(text)
            assert match is None, f"{path.relative_to(REPO_ROOT)}: {label} {match.group()!r}"


def test_website_has_sovereign_ctas() -> None:
    html = (RUNTIME / "website" / "index.html").read_text(encoding="utf-8")
    assert "SOVEREIGN-SETUP" in html or "sovereign" in html.lower()
    assert "INSTALL-USER" in html or "Download" in html