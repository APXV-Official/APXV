"""Resolve STT/TTS providers (local, simulated, or env override)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

from .local_backends import Pyttsx3TTSProvider, VoskSTTProvider
from .providers import (
    APXSTTProvider,
    APXTTSProvider,
    SimulatedSTTProvider,
    SimulatedTTSProvider,
    VoiceBackendError,
)


def voice_mode() -> str:
    return os.environ.get("APX_VOICE_MODE", "local").strip().lower()


def resolve_voice_providers(
    base_path: Path,
    *,
    mode: Optional[str] = None,
    stt_transcript: Optional[str] = None,
) -> Tuple[APXSTTProvider, APXTTSProvider, str]:
    """
    Return (stt, tts, resolved_mode).

    APX_VOICE_MODE:
      - simulated — CI / no model deps
      - local     — Vosk + pyttsx3 when available, else simulated fallback
    """
    selected = (mode or voice_mode()).lower()
    if selected == "simulated":
        return SimulatedSTTProvider(stt_transcript), SimulatedTTSProvider(), "simulated"

    if selected != "local":
        raise ValueError(f"Unknown APX_VOICE_MODE: {selected}")

    stt: APXSTTProvider
    tts: APXTTSProvider
    try:
        stt = VoskSTTProvider(base_path)
        tts = Pyttsx3TTSProvider()
        return stt, tts, "local"
    except VoiceBackendError:
        return SimulatedSTTProvider(stt_transcript), SimulatedTTSProvider(), "simulated-fallback"