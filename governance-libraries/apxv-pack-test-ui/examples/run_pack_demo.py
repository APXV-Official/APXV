"""Pack demo runner for apxv-pack-test-ui."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from agents.runtime import APXRuntime


def _load_agents():
    mod_path = Path(__file__).resolve().parents[1] / "agents" / "custom_agents.py"
    spec = importlib.util.spec_from_file_location("pack_custom_agents", mod_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load pack agents from {mod_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_agents = _load_agents()
run_pack_pipeline = _agents.run_pack_pipeline
SAMPLE_INPUT = _agents.SAMPLE_INPUT


def main() -> int:
    result = run_pack_pipeline()
    print("Pack demo:", result.get("final_status"))
    return 0 if result.get("final_status") == "ATTESTED" else 1


if __name__ == "__main__":
    sys.exit(main())
