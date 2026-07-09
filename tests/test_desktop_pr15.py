"""PR-15 — Desktop MSI + first-launch bootstrap wizard."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if (ROOT / "ui").is_dir():
    REPO_ROOT = ROOT
else:
    REPO_ROOT = ROOT.parent
UI_ROOT = REPO_ROOT / "ui"
DESKTOP_TAURI = UI_ROOT / "apps" / "desktop" / "src-tauri"
WEB = UI_ROOT / "apps" / "web"
SCRIPTS = REPO_ROOT / "scripts"

sys.path.insert(0, str(ROOT))


def test_server_rs_localappdata_resolution():
    server_rs = (DESKTOP_TAURI / "src" / "server.rs").read_text(encoding="utf-8")
    paths_rs = (DESKTOP_TAURI / "src" / "paths.rs").read_text(encoding="utf-8")
    assert "resolve_apxv_root" in server_rs
    assert "spawn_python_module" in server_rs
    assert "LOCALAPPDATA" in paths_rs
    assert "default_local_appdata_root" in paths_rs
    assert "C:\\APXV Official" not in server_rs


def test_bootstrap_tauri_commands():
    lib_rs = (DESKTOP_TAURI / "src" / "lib.rs").read_text(encoding="utf-8")
    bootstrap_rs = (DESKTOP_TAURI / "src" / "bootstrap.rs").read_text(encoding="utf-8")
    assert "run_bootstrap" in bootstrap_rs
    assert "get_bootstrap_status" in bootstrap_rs
    assert "scripts.apxv_bootstrap" in bootstrap_rs
    assert "run_bootstrap" in lib_rs
    assert "get_bootstrap_status" in lib_rs
    assert "sovereign_ready" in lib_rs


def test_tauri_conf_bundles_runtime_payload():
    conf = (DESKTOP_TAURI / "tauri.conf.json").read_text(encoding="utf-8")
    assert "runtime-payload" in conf
    assert '"runtime"' in conf


def test_stage_desktop_runtime_script():
    script = (SCRIPTS / "stage-desktop-runtime.ps1").read_text(encoding="utf-8")
    assert "runtime-payload" in script
    assert "governance-libraries" in script
    assert 'Join-Path $RuntimeRoot "managed"' not in script


def test_bootstrap_page_and_router():
    bootstrap_tsx = (WEB / "src" / "pages" / "BootstrapPage.tsx").read_text(encoding="utf-8")
    router_tsx = (WEB / "src" / "pages" / ".." / "router.tsx").resolve().read_text(encoding="utf-8")
    tauri_ts = (WEB / "src" / "lib" / "tauri.ts").read_text(encoding="utf-8")
    assert "Sovereign setup" in bootstrap_tsx or "sovereign" in bootstrap_tsx.lower()
    assert "/bootstrap" in router_tsx
    assert "run_bootstrap" in tauri_ts
    assert "get_bootstrap_status" in tauri_ts


def test_types_default_root_is_localappdata():
    types_index = (UI_ROOT / "packages" / "types" / "src" / "index.ts").read_text(
        encoding="utf-8"
    )
    assert "LOCALAPPDATA" in types_index
    assert "apxv-v1.3-remaster" not in types_index


def test_tauri_smoke_checks_sovereign_path():
    smoke = (SCRIPTS / "tauri-smoke.ps1").read_text(encoding="utf-8")
    assert "LOCALAPPDATA" in smoke or "resolve_apxv_root" in smoke
    assert "bootstrap" in smoke.lower()


def test_bootstrap_e2e_spec_exists():
    spec = WEB / "e2e" / "bootstrap.spec.ts"
    assert spec.is_file()
    text = spec.read_text(encoding="utf-8")
    assert "bootstrap-preview" in text