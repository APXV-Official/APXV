"""
Prepare APXV runtime for desktop / START-APXV launcher.

Ensures first-run directories and operator key exist, then prints JSON:
  {"ready": true, "api_key": "...", "hint_file": "..."}

Usage:
  py -3 -m scripts.launcher_prepare
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.setup_first_run import ensure_api_key, ensure_directories


def load_operator_key_from_hint(base_path: Path) -> tuple[str | None, str | None]:
    config_dir = base_path / "managed" / "config"
    if not config_dir.is_dir():
        return None, None

    for path in sorted(config_dir.glob("OPERATOR-KEY-*.txt")):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("API Key:"):
                key = line.split(":", 1)[1].strip()
                if key:
                    return key, str(path)
    return None, None


def prepare() -> dict:
    ensure_directories(ROOT)
    key_result = ensure_api_key(ROOT)

    api_key = key_result.get("api_key")
    hint_file = key_result.get("hint_file")

    if not api_key:
        api_key, hint_from_disk = load_operator_key_from_hint(ROOT)
        if hint_from_disk:
            hint_file = hint_from_disk

    if not api_key:
        raise RuntimeError(
            "No operator API key found. Run setup-first-run or START-APXV prepare."
        )

    return {
        "ready": True,
        "api_key": api_key,
        "hint_file": hint_file,
    }


def main() -> int:
    try:
        result = prepare()
        print(json.dumps(result))
        return 0
    except Exception as exc:
        print(json.dumps({"ready": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())