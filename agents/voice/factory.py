"""Resolve STT/TTS providers (local, simulated, or env override)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from ..env import get_env
from ..install_profile import ProductionIntegrationError, get_install_profile, PRODUCTION
from .local_backends import Pyttsx3TTSProvider, VoskSTTProvider
from .providers import (
    APXVSTTProvider,
    APXVTTSProvider,
    SimulatedSTTProvider,
    SimulatedTTSProvider,
    VoiceBackendError,
)


def voice_mode() -> str:
    return get_env("APXV_VOICE_MODE", "local").strip().lower()


def resolve_voice_providers(
    base_path: Path,
    *,
    mode: Optional[str] = None,
    stt_transcript: Optional[str] = None,
) -> Tuple[APXVSTTProvider, APXVTTSProvider, str]:
    """
    Return (stt, tts, resolved_mode).

    APXV_VOICE_MODE:
      - simulated — CI profile only (pytest)
      - local     — Vosk + pyttsx3; production requires Vosk (no fallback)
    """
    selected = (mode or voice_mode()).lower()
    profile = get_install_profile(base_path)

    if selected == "simulated":
        if profile == PRODUCTION:
            raise ProductionIntegrationError(
                "Simulated voice mode is disabled in production profile. "
                "Install Vosk and run: python -m scripts.apxv_bootstrap"
            )
        return SimulatedSTTProvider(stt_transcript), SimulatedTTSProvider(), "simulated"

    if selected != "local":
        raise ValueError(f"Unknown APXV_VOICE_MODE: {selected}")

    stt: APXVSTTProvider
    tts: APXVTTSProvider
    try:
        stt = VoskSTTProvider(base_path)
        tts = Pyttsx3TTSProvider()
        return stt, tts, "local"
    except VoiceBackendError as exc:
        if profile == PRODUCTION:
            raise ProductionIntegrationError(
                "Vosk voice backend required in production profile. "
                "Run: python -m scripts.setup_voice"
            ) from exc
        return SimulatedSTTProvider(stt_transcript), SimulatedTTSProvider(), "simulated-fallback"