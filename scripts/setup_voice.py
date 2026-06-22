"""
Download Vosk small English model for local offline STT.

Model: vosk-model-small-en-us-0.15 (~40 MB)
Stored under: managed/store/voice-models/
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.voice.local_backends import default_vosk_model_dir

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
MODEL_NAME = "vosk-model-small-en-us-0.15"


def ensure_vosk_model(base_path: Path | None = None, *, force: bool = False) -> dict:
    base = base_path or ROOT
    target = default_vosk_model_dir(base)
    if target.exists() and not force:
        return {"status": "present", "path": str(target)}

    models_dir = target.parent
    models_dir.mkdir(parents=True, exist_ok=True)
    zip_path = models_dir / f"{MODEL_NAME}.zip"

    print(f"[Voice Setup] Downloading {MODEL_NAME}...")
    urlretrieve(MODEL_URL, zip_path)

    extract_root = models_dir / "_extract"
    if extract_root.exists():
        shutil.rmtree(extract_root)
    extract_root.mkdir()

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_root)

    extracted = extract_root / MODEL_NAME
    if not extracted.exists():
        candidates = list(extract_root.glob("**/am/final.mdl"))
        if candidates:
            extracted = candidates[0].parent.parent.parent
        else:
            raise RuntimeError("Downloaded Vosk archive layout not recognized")

    if target.exists():
        shutil.rmtree(target)
    shutil.move(str(extracted), str(target))
    shutil.rmtree(extract_root, ignore_errors=True)
    zip_path.unlink(missing_ok=True)

    return {"status": "installed", "path": str(target)}


def main() -> int:
    parser = argparse.ArgumentParser(description="APXV1 voice model setup (Vosk STT)")
    parser.add_argument("--base-path", type=Path, default=ROOT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        report = ensure_vosk_model(args.base_path.resolve(), force=args.force)
        print(f"Vosk model {report['status']}: {report['path']}")
        print("Install voice deps: pip install -e \".[voice]\"")
        return 0
    except Exception as exc:
        print(f"Voice setup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())