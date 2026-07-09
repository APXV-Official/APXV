"""
APXV — API Client Example

Calls the local v1 HTTP API to run the governed pipeline.
Requires apxv_serve to be running and a valid API key.

For new integrations, prefer API v2: POST /api/v2/pipeline/run
See docs/LOCAL-API-V2.md.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agents.env import get_env

DEFAULT_BASE = "http://127.0.0.1:8741"
POLL_SECONDS = 0.5
POLL_TIMEOUT = 120


def api_request(
    method: str,
    path: str,
    *,
    api_key: str | None = None,
    body: dict | None = None,
    base_url: str = DEFAULT_BASE,
) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {path}: {detail}") from exc


def load_api_key() -> str:
    key = get_env("APXV_API_KEY")
    if key:
        return key.strip()

    config_path = ROOT / "managed" / "config" / "api_keys.json"
    if not config_path.exists():
        raise RuntimeError(
            "No API key found. Set APXV_API_KEY or run: python -m scripts.setup_first_run"
        )

    raise RuntimeError(
        "API key hash is stored locally; set APXV_API_KEY env var to the raw key "
        "(printed once during setup_first_run or apxv_serve first start)."
    )


def wait_for_job(job_id: str, api_key: str, base_url: str) -> dict:
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        job = api_request("GET", f"/jobs/{job_id}", api_key=api_key, base_url=base_url)
        status = job.get("status")
        if status in ("completed", "failed"):
            return job
        time.sleep(POLL_SECONDS)
    raise TimeoutError(f"Job {job_id} did not complete within {POLL_TIMEOUT}s")


def main() -> int:
    base_url = get_env("APXV_API_BASE", DEFAULT_BASE) or DEFAULT_BASE
    api_key = load_api_key()

    health = api_request("GET", "/health", base_url=base_url)
    print("Health:", json.dumps(health, indent=2))
    integrity = health.get("integrity", {})
    is_healthy = health.get("status") == "healthy" or integrity.get("healthy", False)
    if not is_healthy:
        print("APXV instance is unhealthy — run: python -m scripts.apxv_ctl integrity")
        return 1

    payload = {
        "input_text": "Contact alice@example.com or call (555) 987-6543.",
        "attest": False,
        "async": True,
    }
    queued = api_request("POST", "/pipeline/run", api_key=api_key, body=payload, base_url=base_url)
    job_id = queued.get("job_id")
    print(f"Queued job: {job_id}")

    job = wait_for_job(job_id, api_key, base_url)
    print("Job result:", json.dumps(job, indent=2))
    return 0 if job.get("status") == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())