"""One-time Groth16 setup for universal-predicate-v1."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.zk.universal_bridge import ensure_universal_setup


def main() -> None:
    force = "--force" in sys.argv
    report = ensure_universal_setup(ROOT, force=force)
    print("universal-predicate-v1 setup:")
    for k, v in report.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
