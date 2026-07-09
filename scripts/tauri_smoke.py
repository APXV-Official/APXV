"""
Row 11 — Tauri desktop smoke (automated).

Verifies the same runtime path Tauri uses (DEFAULT_APXV_ROOT + apxv_serve spawn)
then runs: auth → pack activate → pipeline → artifact.

Usage (API already on :8741):
  py -3 -m scripts.tauri_smoke

Spawn server like Tauri (stop other listeners on 8741 first):
  py -3 -m scripts.tauri_smoke --spawn-server
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APXV_ROOT = ROOT
API_BASE = "http://127.0.0.1:8741"
PACK_ID = "apxv-pack-reference-redaction"
POLL_TIMEOUT = 120


def load_operator_key() -> str:
    for path in sorted((ROOT / "managed" / "config").glob("OPERATOR-KEY-*.txt")):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("API Key:"):
                return line.split(":", 1)[1].strip()
    raise RuntimeError("No OPERATOR-KEY-*.txt found — run setup_first_run or START-APXV")


def api(
    method: str,
    path: str,
    *,
    api_key: str,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Content-Type": "application/json",
        "APXV-API-KEY": api_key,
        "Authorization": f"Bearer {api_key}",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(detail)
        except json.JSONDecodeError:
            parsed = {"error": detail}
        return exc.code, parsed


def wait_health(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{API_BASE}/api/v2/system/health", timeout=3) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(0.5)
    raise TimeoutError(f"API not healthy at {API_BASE} within {timeout}s")


def spawn_apxv_serve() -> subprocess.Popen[bytes]:
    py = "py" if _has_py_launcher() else sys.executable
    args = (
        [py, "-3", "-m", "scripts.apxv_serve", "--bind", "127.0.0.1"]
        if py == "py"
        else [py, "-m", "scripts.apxv_serve", "--bind", "127.0.0.1"]
    )
    return subprocess.Popen(
        args,
        cwd=str(DEFAULT_APXV_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _has_py_launcher() -> bool:
    try:
        subprocess.run(["py", "-3", "--version"], capture_output=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_smoke(*, spawn_server: bool) -> int:
    logs: list[str] = []
    server_proc: subprocess.Popen[bytes] | None = None

    def log(msg: str) -> None:
        print(msg)
        logs.append(msg)

    try:
        log(f"[1/7] DEFAULT_APXV_ROOT = {DEFAULT_APXV_ROOT}")
        if not (DEFAULT_APXV_ROOT / "scripts" / "apxv_serve.py").exists():
            log("FAIL: apxv_serve.py missing under DEFAULT_APXV_ROOT")
            return 1

        api_key = load_operator_key()
        log("[2/7] Operator key loaded from OPERATOR-KEY-*.txt")

        if spawn_server:
            log("[3/7] Spawning apxv_serve (Tauri start_apxv_server equivalent)...")
            server_proc = spawn_apxv_serve()
            wait_health(45.0)
            log(f"     Server started (pid {server_proc.pid})")
        else:
            log("[3/7] Using existing API on :8741")
            wait_health(10.0)

        status, _ = api("POST", "/api/v2/system/repair-audit", api_key=api_key)
        log(f"[4/7] repair-audit -> HTTP {status}")

        status, body = api("GET", "/api/v2/system/status", api_key=api_key)
        if status != 200:
            log(f"FAIL: status auth HTTP {status}: {body}")
            return 1
        log(f"[4/7] Authenticated — runtime {body.get('runtime_version', '?')}")

        status, activated = api(
            "POST",
            f"/api/v2/packs/{PACK_ID}/activate",
            api_key=api_key,
            body={"activated_by": "tauri-smoke"},
        )
        if status != 200:
            log(f"FAIL: pack activate HTTP {status}: {activated}")
            return 1
        log(f"[5/7] Pack activated — {activated.get('pack_id', PACK_ID)}")

        status, queued = api(
            "POST",
            "/api/v2/pipeline/run",
            api_key=api_key,
            body={
                "pack": "reference",
                "input_text": "Tauri smoke: contact ops@apxv.example",
                "attest": False,
                "async": True,
            },
        )
        if status not in (200, 202):
            log(f"FAIL: pipeline HTTP {status}: {queued}")
            return 1
        job_id = queued.get("job_id")
        if not job_id:
            log(f"FAIL: no job_id in response: {queued}")
            return 1
        log(f"[6/7] Pipeline queued — job {job_id}")

        deadline = time.time() + POLL_TIMEOUT
        job_status = "unknown"
        while time.time() < deadline:
            status, job = api("GET", f"/api/v2/jobs/{job_id}", api_key=api_key)
            job_status = job.get("status", "unknown")
            if job_status in ("completed", "failed"):
                break
            time.sleep(0.5)
        if job_status != "completed":
            log(f"FAIL: job {job_id} ended as {job_status}")
            return 1
        log(f"[6/7] Job completed — {job_id}")

        status, artifacts = api("GET", "/api/v2/artifacts?limit=1", api_key=api_key)
        if status != 200 or not artifacts.get("items"):
            log(f"FAIL: artifacts HTTP {status}: {artifacts}")
            return 1
        artifact_hash = artifacts["items"][0].get("artifact_hash")
        log(f"[7/7] Artifact present — {artifact_hash}")

        log("")
        log("PASS — Tauri smoke (onboard path + pack activate + pipeline + artifact)")
        return 0
    finally:
        if server_proc and server_proc.poll() is None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server_proc.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description="Row 11 Tauri smoke")
    parser.add_argument(
        "--spawn-server",
        action="store_true",
        help="Start apxv_serve from DEFAULT_APXV_ROOT (like Tauri desktop)",
    )
    return run_smoke(spawn_server=parser.parse_args().spawn_server)


if __name__ == "__main__":
    raise SystemExit(main())