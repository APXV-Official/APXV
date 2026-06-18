"""
APX v1 — Docker entrypoint

Runs first-time setup if needed, then starts the local API server.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def main() -> int:
    policy_path = ROOT / "managed" / "config" / "capabilities.json"
    if not policy_path.exists():
        print("[entrypoint] No capability policy found — running first-run setup...")
        result = subprocess.run(
            [sys.executable, "-m", "scripts.setup_first_run", "--skip-zk"],
            cwd=str(ROOT),
            check=False,
        )
        if result.returncode != 0:
            return result.returncode

    env = {**dict(**{k: v for k, v in __import__("os").environ.items()}), "APX_CONTAINER_BIND": "1"}
    serve = subprocess.run(
        [sys.executable, "-m", "scripts.apx_serve", "--bind", "0.0.0.0", "--port", "8741"],
        cwd=str(ROOT),
        env=env,
    )
    return serve.returncode


if __name__ == "__main__":
    sys.exit(main())