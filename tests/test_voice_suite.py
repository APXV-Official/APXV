"""Tests for APXV voice privacy suite."""

from __future__ import annotations

import os
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
    resolve_voice_providers,
)


@pytest.fixture(autouse=True)
def simulated_voice_mode(monkeypatch):
    monkeypatch.setenv("APXV_VOICE_MODE", "simulated")


def test_resolve_voice_providers_simulated():
    stt, tts, mode = resolve_voice_providers(ROOT, mode="simulated")
    assert mode == "simulated"
    assert stt.transcribe(b"\x00" * 32).provider == "simulated-stt"
    assert tts.synthesize("hello").provider == "simulated-tts"


def test_voice_pipeline_redacts_pii():
    pipeline = VoicePrivacyPipeline(base_path=ROOT, voice_mode="simulated")
    transcript = "Email me at secret.user@example.com please."
    result = pipeline.process_transcript(transcript)
    assert "secret.user@example.com" not in result.redacted_text
    assert len(result.entities) >= 1
    assert result.voice_redaction_inputs["policy_id"] == str(VOICE_REDACTION_POLICY_ID)


def test_voice_pipeline_audio_round_trip():
    pipeline = VoicePrivacyPipeline(
        base_path=ROOT,
        stt=SimulatedSTTProvider("Call (555) 123-4567 today."),
        tts=SimulatedTTSProvider(),
    )
    audio = SimulatedTTSProvider().synthesize("sample").audio_bytes
    result = pipeline.process_audio(audio, synthesize_redacted=True)
    assert result.tts_audio_bytes
    assert "555" not in result.redacted_text or "[REDACTED" in result.redacted_text


def test_build_voice_session():
    pipeline = VoicePrivacyPipeline(base_path=ROOT, voice_mode="simulated")
    result = pipeline.process_transcript("Contact a@b.com")
    session = pipeline.build_voice_session(result, source="transcript")
    assert session["source"] == "transcript"
    assert session["voice_redaction_inputs"]["entity_count"] == str(len(result.entities))


@pytest.mark.skipif(
    os.environ.get("APXV_VOICE_MODE") == "simulated",
    reason="Local backend test requires APXV_VOICE_MODE=local and vosk model",
)
def test_local_vosk_when_model_present():
    model_dir = ROOT / "managed" / "store" / "voice-models" / "vosk-small-en-us-0.15"
    if not model_dir.exists():
        pytest.skip("Vosk model not installed")
    pipeline = VoicePrivacyPipeline(base_path=ROOT, voice_mode="local")
    assert pipeline.voice_mode in ("local", "simulated-fallback")