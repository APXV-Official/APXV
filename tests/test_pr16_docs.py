"""PR-16 gate: operator-facing docs must not mention deprecated trust shortcuts."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
if (RUNTIME_ROOT / "ui").is_dir():
    REPO_ROOT = RUNTIME_ROOT
else:
    REPO_ROOT = RUNTIME_ROOT.parent
UI_ROOT = REPO_ROOT / "ui"

FORBIDDEN = re.compile(r"skip-zk|Seed-Zk|baked keys", re.IGNORECASE)
INTERNAL_LEAK = re.compile(
    r"02_RnD_Lab|RnD_Lab[/\\]|docs/internal/|APXV Personal Build|APXV-CONTROL-PLANE-ROADMAP",
    re.IGNORECASE,
)
CONTROL_PLANE_BRAND = re.compile(r"APXV Control Plane|control plane", re.IGNORECASE)

OPERATOR_DOC_ROOTS = [
    RUNTIME_ROOT / "docs",
    RUNTIME_ROOT / "website",
    RUNTIME_ROOT / "README.md",
    UI_ROOT / "docs",
    UI_ROOT / "README.md",
    UI_ROOT / "apps" / "web" / "index.html",
]

# RnD-only contributor docs (not shipped in desktop payload or GitHub public tree).
SKIP_FILES = {
    REPO_ROOT / "DEV-QUICKSTART.md",
    REPO_ROOT / "APXV-CONTROL-PLANE-ROADMAP.md",
    REPO_ROOT / "README.md",
    REPO_ROOT / "RENAME-MATRIX.md",
}

SKIP_PARTS = {"internal", "resume"}


def _operator_doc_files() -> list[Path]:
    files: list[Path] = []
    for root in OPERATOR_DOC_ROOTS:
        if root.is_file():
            if root not in SKIP_FILES:
                files.append(root)
        elif root.is_dir():
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if path.suffix.lower() not in {".md", ".html"}:
                    continue
                if any(part in SKIP_PARTS for part in path.parts):
                    continue
                if path in SKIP_FILES:
                    continue
                files.append(path)
    return sorted(set(files))


@pytest.mark.parametrize("doc_path", _operator_doc_files(), ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_operator_docs_no_deprecated_trust_shortcuts(doc_path: Path) -> None:
    text = doc_path.read_text(encoding="utf-8", errors="replace")
    match = FORBIDDEN.search(text)
    assert match is None, (
        f"{doc_path.relative_to(REPO_ROOT)} contains forbidden pattern {match.group()!r}"
    )


def test_sovereign_setup_doc_exists() -> None:
    assert (RUNTIME_ROOT / "docs" / "SOVEREIGN-SETUP.md").is_file()


def test_install_user_doc_exists() -> None:
    assert (RUNTIME_ROOT / "docs" / "INSTALL-USER.md").is_file()


@pytest.mark.parametrize("doc_path", _operator_doc_files(), ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_operator_docs_no_internal_path_leaks(doc_path: Path) -> None:
    text = doc_path.read_text(encoding="utf-8", errors="replace")
    match = INTERNAL_LEAK.search(text)
    assert match is None, (
        f"{doc_path.relative_to(REPO_ROOT)} leaks internal path {match.group()!r}"
    )


@pytest.mark.parametrize("doc_path", _operator_doc_files(), ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_operator_docs_no_control_plane_branding(doc_path: Path) -> None:
    text = doc_path.read_text(encoding="utf-8", errors="replace")
    match = CONTROL_PLANE_BRAND.search(text)
    assert match is None, (
        f"{doc_path.relative_to(REPO_ROOT)} uses deprecated branding {match.group()!r}"
    )


def test_staged_payload_excludes_internal_docs() -> None:
    payload_docs = UI_ROOT / "apps" / "desktop" / "runtime-payload" / "docs"
    if not payload_docs.is_dir():
        pytest.skip("runtime-payload not staged in this workspace")
    assert not (payload_docs / "internal").exists()
    assert not (payload_docs / "resume").exists()


def test_staged_payload_includes_governance_seed_specs() -> None:
    payload = UI_ROOT / "apps" / "desktop" / "runtime-payload" / "managed"
    if not payload.parent.is_dir():
        pytest.skip("runtime-payload not staged in this workspace")
    for spec in ("rules/rule1.md", "workflows/workflow1.md", "knowledge/knowledge1.md"):
        path = payload / spec
        assert path.is_file(), f"missing governance seed spec: {spec}"