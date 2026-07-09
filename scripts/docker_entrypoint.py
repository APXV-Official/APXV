"""
APXV — Docker entrypoint

Runs sovereign bootstrap when required, then starts the local API server.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def needs_sovereign_bootstrap(base_path: Path) -> bool:
    """True when instance lacks sovereign ZK keys and install provenance."""
    from scripts.bootstrap.install_json import read_install_json
    from scripts.setup_first_run import verify_entity_zk_keys, verify_zk_keys

    install = read_install_json(base_path)
    zk = verify_zk_keys(base_path)
    entity = verify_entity_zk_keys(base_path)
    keys_ready = bool(zk.get("ready") and entity.get("ready"))

    if install and install.get("sovereign_setup") and keys_ready:
        return False

    if keys_ready and (base_path / "managed" / "config" / "capabilities.json").is_file():
        return False

    return True


def run_bootstrap_if_needed(base_path: Path) -> int:
    if not needs_sovereign_bootstrap(base_path):
        return 0

    print("[entrypoint] Sovereign bootstrap required (keys on operator volumes)...")
    env = {**os.environ, "APXV_CONTAINER_BIND": "1", "APXV_BASE_PATH": str(base_path)}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.apxv_bootstrap",
            "--skip-ollama",
            "--skip-voice",
            "--skip-smoke",
            "--skip-prover-build",
        ],
        cwd=str(base_path),
        env=env,
        check=False,
    )
    # 0 = healthy, 2 = sovereign ok but optional integrations incomplete
    if result.returncode in (0, 2):
        return 0
    return result.returncode


def main() -> int:
    code = run_bootstrap_if_needed(ROOT)
    if code != 0:
        return code

    env = {**os.environ, "APXV_CONTAINER_BIND": "1", "APXV_BASE_PATH": str(ROOT)}
    serve = subprocess.run(
        [sys.executable, "-m", "scripts.apxv_serve", "--bind", "0.0.0.0", "--port", "8741"],
        cwd=str(ROOT),
        env=env,
        check=False,
    )
    return serve.returncode


if __name__ == "__main__":
    sys.exit(main())