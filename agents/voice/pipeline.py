"""Voice privacy pipeline: STT → redact → voice-redaction ZK inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.redaction import APXRedactionEngine
from agents.zk.entity_commitment import string_to_field
from agents.zk.poseidon_client import PoseidonClient

from .providers import APXSTTProvider, APXTTSProvider, SimulatedSTTProvider, SimulatedTTSProvider

# voice-redaction circuit: policy_id 3 = redaction policy (see rust/apx-zk voice_redaction.rs)
VOICE_REDACTION_POLICY_ID = 3


@dataclass
class VoicePipelineResult:
    transcript: str
    redacted_text: str
    entities: List[Dict[str, Any]]
    voice_redaction_inputs: Dict[str, str]
    tts_audio_bytes: Optional[bytes] = None


class VoicePrivacyPipeline:
    def __init__(
        self,
        base_path: Optional[Path] = None,
        *,
        stt: Optional[APXSTTProvider] = None,
        tts: Optional[APXTTSProvider] = None,
        poseidon: Optional[PoseidonClient] = None,
    ) -> None:
        self.base_path = base_path or Path(__file__).parent.parent.parent
        self.stt = stt or SimulatedSTTProvider()
        self.tts = tts or SimulatedTTSProvider()
        self.redaction = APXRedactionEngine()
        self.poseidon = poseidon or PoseidonClient(base_path=self.base_path)

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
        )

    def process_transcript(
        self,
        transcript: str,
        *,
        synthesize_redacted: bool = False,
    ) -> VoicePipelineResult:
        redaction = self.redaction.redact_pii(transcript)
        redacted_text = redaction.get("redacted_text", transcript)
        entities = redaction.get("entities", [])
        inputs = self.build_voice_redaction_inputs(transcript, redacted_text, entities)

        tts_bytes = None
        if synthesize_redacted:
            tts_bytes = self.tts.synthesize(redacted_text).audio_bytes

        return VoicePipelineResult(
            transcript=transcript,
            redacted_text=redacted_text,
            entities=entities,
            voice_redaction_inputs=inputs,
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