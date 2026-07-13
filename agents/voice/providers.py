"""Pluggable STT/TTS providers for the APXV voice privacy suite."""

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


class VoiceBackendError(Exception):
    """Raised when a local voice backend is unavailable."""


class APXVSTTProvider(Protocol):
    def transcribe(self, audio_bytes: bytes, *, mime_type: str = "audio/wav") -> STTResult:
        ...


class APXVTTSProvider(Protocol):
    def synthesize(self, text: str, *, voice_id: str = "default") -> TTSResult:
        ...


class SimulatedSTTProvider:
    """Deterministic STT for CI and air-gapped demos without audio models."""

    def __init__(self, transcript: str | None = None):
        self._transcript = transcript or (
            "Contact John at john.doe@example.com or call (555) 123-4567."
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
    """Minimal WAV payload for tests (not intelligible speech)."""

    def synthesize(self, text: str, *, voice_id: str = "default") -> TTSResult:
        import struct
        import wave
        from io import BytesIO

        sample_rate = 16000
        duration_sec = min(2.0, max(0.2, len(text) / 40.0))
        n_frames = int(sample_rate * duration_sec)
        buf = BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            silence = struct.pack("<h", 0) * n_frames
            wf.writeframes(silence)
        return TTSResult(
            audio_bytes=buf.getvalue(),
            sample_rate_hz=sample_rate,
            provider="simulated-tts",
        )


# v1.3.x compat — removed in v1.4
APXSTTProvider = APXVSTTProvider
APXTTSProvider = APXVTTSProvider