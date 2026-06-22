"""APXV1 voice privacy demo — STT → redact → optional voice-redaction ZK prove."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.voice import VoicePrivacyPipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="APXV1 voice privacy demo")
    parser.add_argument("--base-path", type=Path, default=ROOT)
    parser.add_argument("--voice-file", type=Path, help="WAV audio input")
    parser.add_argument("--transcript", type=str, help="Skip STT; use this transcript")
    parser.add_argument("--voice-mode", choices=["local", "simulated"], default=None)
    parser.add_argument("--real-zk", action="store_true")
    parser.add_argument("--synthesize", action="store_true")
    args = parser.parse_args()

    pipeline = VoicePrivacyPipeline(base_path=args.base_path.resolve(), voice_mode=args.voice_mode)

    if args.transcript:
        result = pipeline.process_transcript(args.transcript, synthesize_redacted=args.synthesize)
    elif args.voice_file:
        audio = args.voice_file.read_bytes()
        result = pipeline.process_audio(audio, synthesize_redacted=args.synthesize)
    else:
        from agents.voice.providers import SimulatedTTSProvider

        sample_text = (
            "Contact John at john.doe@example.com or call (555) 123-4567."
        )
        audio = SimulatedTTSProvider().synthesize(sample_text).audio_bytes
        result = pipeline.process_audio(audio, synthesize_redacted=args.synthesize)

    print("=" * 60)
    print("APXV1 Voice Privacy Demo")
    print("=" * 60)
    print(f"Voice mode: {result.voice_mode}")
    print(f"STT: {result.stt_provider}")
    print(f"Transcript: {result.transcript[:100]}...")
    print(f"Redacted:   {result.redacted_text[:100]}...")
    print(f"Entities:   {len(result.entities)}")
    print(json.dumps(result.voice_redaction_inputs, indent=2))

    if args.real_zk:
        from agents.zk.bridge import EntityZKBridge
        from scripts.setup_entity_zk import ensure_entity_zk_setup

        ensure_entity_zk_setup(base_path=args.base_path)
        bridge = EntityZKBridge(base_path=args.base_path)
        proof = bridge.prove_circuit("voice-redaction", result.voice_redaction_inputs)
        print(json.dumps(
            {k: proof.get(k) for k in ("verification_result", "status", "circuit_version")},
            indent=2,
        ))
        if not proof.get("verification_result"):
            return 1

    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())