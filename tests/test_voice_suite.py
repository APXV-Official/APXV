"""Tests for APXV1 voice privacy suite (v1.1 scaffold)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.voice import (
    SimulatedSTTProvider,
    SimulatedTTSProvider,
    VOICE_REDACTION_POLICY_ID,
    VoicePrivacyPipeline,
)


def test_simulated_stt_transcribe():
    stt = SimulatedSTTProvider("hello world")
    result = stt.transcribe(b"\x00" * 64)
    assert result.transcript == "hello world"
    assert result.provider == "simulated-stt"


def test_voice_pipeline_redacts_pii():
    pipeline = VoicePrivacyPipeline(base_path=ROOT)
    transcript = "Email me at secret.user@example.com please."
    result = pipeline.process_transcript(transcript)
    assert "secret.user@example.com" not in result.redacted_text
    assert len(result.entities) >= 1
    assert result.voice_redaction_inputs["policy_id"] == str(VOICE_REDACTION_POLICY_ID)
    assert int(result.voice_redaction_inputs["entity_count"]) >= 1


def test_voice_pipeline_from_audio_bytes():
    pipeline = VoicePrivacyPipeline(
        base_path=ROOT,
        stt=SimulatedSTTProvider("Call (555) 123-4567 today."),
    )
    result = pipeline.process_audio(b"demo-audio", synthesize_redacted=True)
    assert result.tts_audio_bytes
    assert "555" not in result.redacted_text or "[REDACTED" in result.redacted_text


@pytest.mark.skipif(
    not (ROOT / "rust" / "target" / "release" / "apx-zk").exists()
    and not (ROOT / "rust" / "target" / "release" / "apx-zk.exe").exists(),
    reason="apx-zk release binary required",
)
def test_voice_redaction_zk_prove():
    from agents.zk.bridge import EntityZKBridge
    from scripts.setup_entity_zk import ensure_entity_zk_setup

    ensure_entity_zk_setup(base_path=ROOT)
    pipeline = VoicePrivacyPipeline(base_path=ROOT)
    result = pipeline.process_transcript(
        "Contact John at john.doe@example.com or call (555) 123-4567."
    )
    bridge = EntityZKBridge(base_path=ROOT)
    proof = bridge.prove_circuit("voice-redaction", result.voice_redaction_inputs)
    assert proof.get("verification_result") is True, proof