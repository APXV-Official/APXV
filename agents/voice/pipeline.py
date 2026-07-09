"""Voice privacy pipeline: STT → redact → voice-redaction ZK inputs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.redaction import APXVRedactionEngine
from agents.zk.entity_commitment import string_to_field

from .factory import resolve_voice_providers
from .providers import APXVSTTProvider, APXVTTSProvider

# voice-redaction circuit: policy_id 3 = redaction policy (rust/apxv-zk voice_redaction.rs)
VOICE_REDACTION_POLICY_ID = 3


@dataclass
class VoicePipelineResult:
    transcript: str
    redacted_text: str
    entities: List[Dict[str, Any]]
    voice_redaction_inputs: Dict[str, str]
    stt_provider: str
    tts_provider: str
    voice_mode: str
    tts_audio_bytes: Optional[bytes] = None


class VoicePrivacyPipeline:
    def __init__(
        self,
        base_path: Optional[Path] = None,
        *,
        stt: Optional[APXVSTTProvider] = None,
        tts: Optional[APXVTTSProvider] = None,
        voice_mode: Optional[str] = None,
    ) -> None:
        self.base_path = base_path or Path(__file__).resolve().parent.parent.parent
        if stt is not None and tts is not None:
            self.stt = stt
            self.tts = tts
            self.voice_mode = voice_mode or "custom"
        else:
            self.stt, self.tts, self.voice_mode = resolve_voice_providers(
                self.base_path, mode=voice_mode
            )
        self.redaction = APXVRedactionEngine()

    def process_audio(
        self,
        audio_bytes: bytes,
        *,
        mime_type: str = "audio/wav",
        synthesize_redacted: bool = False,
    ) -> VoicePipelineResult:
        stt_out = self.stt.transcribe(audio_bytes, mime_type=mime_type)
        return self.process_transcript(
            stt_out.transcript,
            synthesize_redacted=synthesize_redacted,
            stt_provider=stt_out.provider,
        )

    def process_transcript(
        self,
        transcript: str,
        *,
        synthesize_redacted: bool = False,
        stt_provider: str = "transcript",
    ) -> VoicePipelineResult:
        redaction = self.redaction.redact_pii(transcript)
        redacted_text = redaction.get("redacted_text", transcript)
        entities = redaction.get("entities", [])
        inputs = self.build_voice_redaction_inputs(transcript, redacted_text, entities)

        tts_bytes = None
        tts_provider = "none"
        if synthesize_redacted:
            tts_out = self.tts.synthesize(redacted_text)
            tts_bytes = tts_out.audio_bytes
            tts_provider = tts_out.provider

        return VoicePipelineResult(
            transcript=transcript,
            redacted_text=redacted_text,
            entities=entities,
            voice_redaction_inputs=inputs,
            stt_provider=stt_provider,
            tts_provider=tts_provider,
            voice_mode=self.voice_mode,
            tts_audio_bytes=tts_bytes,
        )

    def build_voice_redaction_inputs(
        self,
        original: str,
        redacted: str,
        entities: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        entity_count = len(entities)
        return {
            "entity_count": str(entity_count),
            "policy_id": str(VOICE_REDACTION_POLICY_ID),
            "original_hash": str(string_to_field(original)),
            "redacted_hash": str(string_to_field(redacted)),
        }

    def build_voice_session(
        self,
        result: VoicePipelineResult,
        *,
        source: str,
        audio_sha256: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "source": source,
            "voice_mode": result.voice_mode,
            "stt_provider": result.stt_provider,
            "tts_provider": result.tts_provider,
            "transcript_sha256": hashlib.sha256(result.transcript.encode("utf-8")).hexdigest(),
            "audio_sha256": audio_sha256,
            "entity_count": len(result.entities),
            "entities": result.entities,
            "voice_redaction_inputs": result.voice_redaction_inputs,
        }