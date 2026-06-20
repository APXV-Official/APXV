"""
APXV1 voice privacy demo — STT → redact → voice-redaction ZK prove (v1.1).

Uses simulated STT by default (no external models). Pass --real-zk to invoke apx-zk.
"""

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
    parser.add_argument("--real-zk", action="store_true", help="Prove voice-redaction with apx-zk")
    parser.add_argument("--synthesize", action="store_true", help="Run simulated TTS on redacted text")
    args = parser.parse_args()

    pipeline = VoicePrivacyPipeline(base_path=args.base_path.resolve())
    sample_audio = b"WAV-demo-" + b"\x00" * 128
    result = pipeline.process_audio(sample_audio, synthesize_redacted=args.synthesize)

    print("=" * 60)
    print("APXV1 Voice Privacy Demo")
    print("=" * 60)
    print(f"Transcript: {result.transcript[:80]}...")
    print(f"Redacted:   {result.redacted_text[:80]}...")
    print(f"Entities:   {len(result.entities)}")
    print()
    print("voice-redaction public inputs:")
    print(json.dumps(result.voice_redaction_inputs, indent=2))

    if args.real_zk:
        from agents.zk.bridge import EntityZKBridge
        from scripts.setup_entity_zk import ensure_entity_zk_setup

        ensure_entity_zk_setup(base_path=args.base_path)
        bridge = EntityZKBridge(base_path=args.base_path)
        proof = bridge.prove_circuit("voice-redaction", result.voice_redaction_inputs)
        print()
        print("ZK prove result:")
        print(json.dumps(
            {k: proof.get(k) for k in ("verification_result", "status", "circuit_version", "vk_hash")},
            indent=2,
        ))
        if not proof.get("verification_result"):
            return 1

    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())