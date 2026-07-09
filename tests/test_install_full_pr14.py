"""PR-14 — install-full native sovereign bootstrap scripts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_install_full_ps1_sovereign_flow():
    script = (ROOT / "scripts" / "install-full.ps1").read_text(encoding="utf-8")
    assert "cargo build --release" in script
    assert "scripts.apxv_bootstrap" in script
    assert "--profile" in script and "production" in script
    assert "scripts.onboard" in script and "--skip-setup" in script
    assert "--skip-smoke" in script
    assert "install-docker.ps1" in script


def test_install_full_sh_sovereign_flow():
    script = (ROOT / "scripts" / "install-full.sh").read_text(encoding="utf-8")
    assert "cargo build --release" in script
    assert "scripts.apxv_bootstrap" in script
    assert "--profile production" in script
    assert "scripts.onboard" in script and "--skip-setup" in script
    assert "--skip-smoke" in script
    assert "install-docker.sh" in script


def test_install_ps1_redirects_to_install_full():
    script = (ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")
    assert "deprecated" in script.lower()
    assert "install-full.ps1" in script
    assert "install-docker.ps1" in script


def test_install_sh_redirects_to_install_full():
    script = (ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
    assert "deprecated" in script.lower()
    assert "install-full.sh" in script
    assert "install-docker.sh" in script


def test_install_full_optional_integration_flags():
    ps1 = (ROOT / "scripts" / "install-full.ps1").read_text(encoding="utf-8")
    sh = (ROOT / "scripts" / "install-full.sh").read_text(encoding="utf-8")
    assert "SkipOllama" in ps1
    assert "SkipVoice" in ps1
    assert "--skip-ollama" in sh
    assert "--skip-voice" in sh
    bootstrap_block = sh.split("BOOTSTRAP_ARGS=(")[1].split(")")[0]
    assert "--skip-ollama" not in bootstrap_block
    assert "--skip-voice" not in bootstrap_block


def test_onboard_docstring_references_install_full():
    onboard = (ROOT / "scripts" / "onboard.py").read_text(encoding="utf-8")
    assert "install-full" in onboard