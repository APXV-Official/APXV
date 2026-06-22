"""End-to-end voice + dual ZK attestation tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

VOICE_SAMPLE = (
    "Contact John at john.doe@example.com or call (555) 123-4567. "
    "SSN: 123-45-6789."
)


@pytest.fixture(autouse=True)
def simulated_voice_mode(monkeypatch):
    monkeypatch.setenv("APX_VOICE_MODE", "simulated")


@pytest.mark.skipif(
    not (ROOT / "rust" / "Cargo.toml").exists(),
    reason="Rust workspace not available",
)
def test_voice_transcript_attest_and_verify():
    env = {**os.environ, "APX_VOICE_MODE": "simulated"}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.run_apx",
            "--voice-transcript",
            VOICE_SAMPLE,
            "--attest",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=900,
        env=env,
    )
    assert result.returncode == 0, result.stderr[-1200:]

    verify = subprocess.run(
        [sys.executable, "-m", "scripts.verify_attestation", "--real-zk"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=900,
        env=env,
    )
    assert verify.returncode == 0, verify.stdout + verify.stderr
    assert "ALL GOVERNANCE + ENTITY GROTH16 PROOFS INDEPENDENTLY VERIFIED" in verify.stdout

    artifacts = sorted((ROOT / "managed" / "artifacts").glob("attested_result_pipeline_with_zk_*.json"))
    assert artifacts
    import json

    wrapped = json.loads(artifacts[-1].read_text(encoding="utf-8"))
    attested = wrapped.get("artifact", wrapped)
    assert "voice_session" in attested
    assert "voice_redaction" in attested.get("entity_proofs", {}).get("proofs", {})