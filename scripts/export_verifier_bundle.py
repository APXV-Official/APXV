"""
Export verifier-only ZK artifacts (VK + manifests, no proving keys).

Safe to publish for third-party Groth16 verification.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

README_SNIPPET = """# APXV Verifier Bundle

Verification keys and manifests only — **no proving keys**.

## Contents

- `governance/` — apxv-circuits VKs + manifest.json
- `entity/` — apxv-zk VKs + entity-manifest.json
- `ceremony-transcript.json` — optional signed transcript (if copied)

## Verify an attestation

```bash
python -m scripts.verify_attestation --real-zk /path/to/attested_artifact.json
```

Confirm proof bundle `vk_hex` matches on-disk VK bytes hashed in the manifests.

See docs/cryptography/CEREMONY.md for ceremony tiers and limitations.
"""


def export_verifier_bundle(
    dest: Path,
    base_path: Optional[Path] = None,
    *,
    include_transcript: bool = True,
) -> Path:
    base = base_path or ROOT
    dest = dest.resolve()
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    gov_src = base / "rust" / "apxv-circuits" / "keys"
    ent_src = base / "rust" / "apxv-zk" / "keys"
    gov_dest = dest / "governance"
    ent_dest = dest / "entity"
    gov_dest.mkdir()
    ent_dest.mkdir()

    shutil.copy2(gov_src / "manifest.json", gov_dest / "manifest.json")
    for vk in gov_src.glob("*.vk"):
        shutil.copy2(vk, gov_dest / vk.name)

    shutil.copy2(ent_src / "entity-manifest.json", ent_dest / "entity-manifest.json")
    for vk in ent_src.glob("*.vk"):
        shutil.copy2(vk, ent_dest / vk.name)

    transcript_src = base / "managed" / "config" / "ceremony-transcript.json"
    if include_transcript and transcript_src.exists():
        shutil.copy2(transcript_src, dest / "ceremony-transcript.json")

    (dest / "README.md").write_text(README_SNIPPET, encoding="utf-8")
    manifest = {
        "bundle_version": "1.0.0",
        "governance_circuits": sorted(p.stem for p in gov_dest.glob("*.vk")),
        "entity_circuits": sorted(p.stem for p in ent_dest.glob("*.vk")),
        "includes_transcript": include_transcript and transcript_src.exists(),
    }
    (dest / "bundle-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Export APXV verifier-only bundle")
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    parser.add_argument("--base-path", type=Path, default=ROOT)
    parser.add_argument("--no-transcript", action="store_true")
    args = parser.parse_args()

    path = export_verifier_bundle(
        args.out,
        base_path=args.base_path.resolve(),
        include_transcript=not args.no_transcript,
    )
    print(f"Verifier bundle exported: {path}")
    print(f"  Governance VKs: {len(list((path / 'governance').glob('*.vk')))}")
    print(f"  Entity VKs: {len(list((path / 'entity').glob('*.vk')))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())