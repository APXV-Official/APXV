"""Pluggable STT/TTS providers for the APXV1 voice privacy suite."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class STTResult:
    transcript: str
    language: str = "en"
    duration_ms: int = 0
    provider: str = ""


@dataclass
class TTSResult:
    audio_bytes: bytes
    sample_rate_hz: int = 16000
    provider: str = ""


class APXSTTProvider(Protocol):
    """Speech-to-text backend. Implement for Whisper, cloud APIs, etc."""

    def transcribe(self, audio_bytes: bytes, *, mime_type: str = "audio/wav") -> STTResult:
        ...


class APXTTSProvider(Protocol):
    """Text-to-speech backend. Implement for Piper, cloud APIs, etc."""

    def synthesize(self, text: str, *, voice_id: str = "default") -> TTSResult:
        ...


class SimulatedSTTProvider:
    """Deterministic STT for tests and air-gapped demos without audio models."""

    def __init__(self, transcript: str | None = None):
        self._transcript = transcript or (
            "Contact John at john.doe@example.com or call five five five one two three four five six seven."
        )

    def transcribe(self, audio_bytes: bytes, *, mime_type: str = "audio/wav") -> STTResult:
        _ = (audio_bytes, mime_type)
        return STTResult(
            transcript=self._transcript,
            language="en",
            duration_ms=max(1, len(audio_bytes) // 32),
            provider="simulated-stt",
        )


class SimulatedTTSProvider:
    """Placeholder audio output — encodes length metadata only (no real waveform)."""

    def synthesize(self, text: str, *, voice_id: str = "default") -> TTSResult:
        payload = f"TTS:{voice_id}:{len(text)}".encode("utf-8")
        return TTSResult(audio_bytes=payload, sample_rate_hz=16000, provider="simulated-tts")