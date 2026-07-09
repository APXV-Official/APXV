"""PR-18 — Desktop macOS + Linux release (cross-platform shell, staging, bundles)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if (ROOT / "ui").is_dir():
    REPO_ROOT = ROOT
else:
    REPO_ROOT = ROOT.parent
UI_ROOT = REPO_ROOT / "ui"
DESKTOP_TAURI = UI_ROOT / "apps" / "desktop" / "src-tauri"
SCRIPTS = REPO_ROOT / "scripts"

sys.path.insert(0, str(ROOT))


def test_python_cmd_module_exists():
    python_cmd = (DESKTOP_TAURI / "src" / "python_cmd.rs").read_text(encoding="utf-8")
    lib_rs = (DESKTOP_TAURI / "src" / "lib.rs").read_text(encoding="utf-8")
    server_rs = (DESKTOP_TAURI / "src" / "server.rs").read_text(encoding="utf-8")
    bootstrap_rs = (DESKTOP_TAURI / "src" / "bootstrap.rs").read_text(encoding="utf-8")
    assert "spawn_python_module" in python_cmd
    assert "mod python_cmd" in lib_rs
    assert "spawn_python_module" in server_rs
    assert "spawn_python_module" in bootstrap_rs
    assert 'Command::new("py")' not in server_rs
    assert '"-3"' not in bootstrap_rs
    assert "scripts.apxv_bootstrap" in bootstrap_rs


def test_paths_cross_platform_markers():
    paths_rs = (DESKTOP_TAURI / "src" / "paths.rs").read_text(encoding="utf-8")
    assert "LOCALAPPDATA" in paths_rs
    assert "Application Support" in paths_rs
    assert "XDG_DATA_HOME" in paths_rs
    assert "default_local_appdata_root" in paths_rs


def test_tauri_conf_cross_platform_targets():
    conf = json.loads((DESKTOP_TAURI / "tauri.conf.json").read_text(encoding="utf-8"))
    targets = conf["bundle"]["targets"]
    assert "msi" in targets
    assert "dmg" in targets
    assert "app" in targets
    assert "deb" in targets
    assert "appimage" in targets


def test_unix_stage_and_build_scripts():
    stage = (SCRIPTS / "stage-desktop-runtime.sh").read_text(encoding="utf-8")
    build = (SCRIPTS / "build-desktop.sh").read_text(encoding="utf-8")
    smoke = (SCRIPTS / "tauri-smoke.sh").read_text(encoding="utf-8")
    assert "runtime-payload" in stage
    assert "governance-libraries" in stage
    assert "filter_release_binaries" in stage or "*.exe" in stage
    assert "stage-desktop-runtime.sh" in build
    assert "cargo build --release" in build
    assert "spawn_python_module" in smoke or "python_cmd.rs" in smoke
    assert "Application Support" in smoke or "XDG_DATA_HOME" in smoke


def test_windows_stage_filters_unix_binaries():
    script = (SCRIPTS / "stage-desktop-runtime.ps1").read_text(encoding="utf-8")
    assert "apxv-zk" in script
    assert "runtime-payload" in script


def test_rust_bins_prefers_native_on_unix():
    rust_bins = (ROOT / "scripts" / "rust_bins.py").read_text(encoding="utf-8")
    assert "_release_binary_names" in rust_bins
    assert "platform.system()" in rust_bins
    assert 'return (stem, f"{stem}.exe")' in rust_bins or "stem, f\"{stem}.exe\"" in rust_bins


def test_dev_quickstart_lists_desktop_platforms():
    candidates = [
        REPO_ROOT / "DEV-QUICKSTART.md",
        UI_ROOT / "apps" / "desktop" / "README.md",
    ]
    quickstart = next((p for p in candidates if p.is_file()), None)
    assert quickstart is not None, "expected DEV-QUICKSTART.md or desktop README"
    text = quickstart.read_text(encoding="utf-8")
    assert "macOS" in text or "Linux" in text
    assert "build-desktop.sh" in text or "Desktop" in text