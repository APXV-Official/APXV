"""Local offline STT (Vosk) and TTS (pyttsx3) backends."""

from __future__ import annotations

import json
import tempfile
import wave
from io import BytesIO
from pathlib import Path
from typing import Optional

from .providers import STTResult, TTSResult, VoiceBackendError


def default_vosk_model_dir(base_path: Path) -> Path:
    return base_path / "managed" / "store" / "voice-models" / "vosk-small-en-us-0.15"


class VoskSTTProvider:
    """Offline speech-to-text via Vosk (Kaldi). Requires model under managed/store/voice-models/."""

    def __init__(self, base_path: Path, *, model_dir: Optional[Path] = None):
        self.model_dir = model_dir or default_vosk_model_dir(base_path)
        if not self.model_dir.exists():
            raise VoiceBackendError(
                f"Vosk model not found at {self.model_dir}. "
                "Run: python -m scripts.setup_voice"
            )
        try:
            from vosk import Model, SetLogLevel
        except ImportError as exc:
            raise VoiceBackendError(
                "vosk package not installed. Run: pip install -e \".[voice]\""
            ) from exc
        SetLogLevel(-1)
        self._model = Model(str(self.model_dir))

    def transcribe(self, audio_bytes: bytes, *, mime_type: str = "audio/wav") -> STTResult:
        from vosk import KaldiRecognizer

        _ = mime_type
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = Path(tmp.name)

        try:
            with wave.open(str(tmp_path), "rb") as wf:
                if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                    raise VoiceBackendError("Vosk requires mono 16-bit PCM WAV input")
                sample_rate = wf.getframerate()
                recognizer = KaldiRecognizer(self._model, sample_rate)
                recognizer.SetWords(True)
                frames = wf.readframes(wf.getnframes())
                recognizer.AcceptWaveform(frames)
                result = json.loads(recognizer.FinalResult())
        finally:
            tmp_path.unlink(missing_ok=True)

        text = (result.get("text") or "").strip()
        if not text:
            raise VoiceBackendError("Vosk produced empty transcript — audio may be silent or unsupported")

        duration_ms = int((len(frames) / (sample_rate * 2)) * 1000) if sample_rate else 0
        return STTResult(
            transcript=text,
            language="en",
            duration_ms=duration_ms,
            provider="vosk",
        )


class Pyttsx3TTSProvider:
    """Offline TTS via pyttsx3 (Windows SAPI / Linux espeak / macOS nsss)."""

    def __init__(self) -> None:
        try:
            import pyttsx3
        except ImportError as exc:
            raise VoiceBackendError(
                "pyttsx3 not installed. Run: pip install -e \".[voice]\""
            ) from exc
        self._engine = pyttsx3.init()

    def synthesize(self, text: str, *, voice_id: str = "default") -> TTSResult:
        _ = voice_id
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            out_path = Path(tmp.name)
        try:
            self._engine.save_to_file(text, str(out_path))
            self._engine.runAndWait()
            if not out_path.exists() or out_path.stat().st_size < 44:
                raise VoiceBackendError("pyttsx3 did not produce WAV output")
            audio_bytes = out_path.read_bytes()
            with wave.open(str(out_path), "rb") as wf:
                sample_rate = wf.getframerate()
        finally:
            out_path.unlink(missing_ok=True)

        return TTSResult(
            audio_bytes=audio_bytes,
            sample_rate_hz=sample_rate,
            provider="pyttsx3",
        )