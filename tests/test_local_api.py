"""Tests for local APX API server (Phase 4 Step 1)."""

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.auth import APIKeyAuth
from agents.job_queue import JobQueue
from agents.local_api import APXLocalServer, validate_localhost_bind
from agents.pipeline_service import run_pipeline_quiet

from tests.helpers import seed_test_instance


def test_api_key_hash_validation(tmp_path):
    config = tmp_path / "api_keys.json"
    auth = APIKeyAuth(config)
    raw = auth.ensure_default_key()
    assert raw is not None
    assert auth.validate(raw) is True
    assert auth.validate("wrong-key") is False


def test_job_queue_lifecycle(tmp_path):
    queue = JobQueue(tmp_path / "jobs.db")
    job = queue.enqueue("pipeline", {"input_text": "test", "attest": False})
    assert job["status"] == "queued"

    claimed = queue.claim_next("pipeline")
    assert claimed["id"] == job["job_id"]
    assert claimed["status"] == "running"

    queue.complete(job["job_id"], {"ok": True})
    loaded = queue.get(job["job_id"])
    assert loaded["status"] == "completed"
    assert loaded["result"]["ok"] is True


def test_pipeline_service_quiet():
    result = run_pipeline_quiet(input_text="no pii here", attest=False)
    assert result["final_status"] == "ATTESTED"
    assert result["artifact_hash"]


def _request(url: str, method: str = "GET", data: dict | None = None, headers: dict | None = None):
    body = None
    req_headers = headers or {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


@pytest.fixture
def api_server(tmp_path):
    api_key = seed_test_instance(tmp_path)
    config_dir = tmp_path / "managed" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "server.json").write_text(
        json.dumps({"bind_address": "127.0.0.1", "port": 0, "require_auth": True}),
        encoding="utf-8",
    )
    server = APXLocalServer(base_path=tmp_path)
    if not api_key:
        auth = APIKeyAuth(tmp_path / "managed" / "config" / "api_keys.json")
        api_key = auth.create_key("pytest-operator", description="API test fixture key")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.address
    base = f"http://{host}:{port}"
    for _ in range(50):
        try:
            _request(f"{base}/health")
            break
        except Exception:
            time.sleep(0.1)
    else:
        pytest.fail("API server did not become ready")
    yield base, api_key
    server.worker.stop()
    server.httpd.shutdown()


def test_rejects_non_localhost_bind():
    with pytest.raises(ValueError, match="localhost only"):
        validate_localhost_bind("0.0.0.0")


def test_health_endpoint(api_server):
    base, _ = api_server
    status, data = _request(f"{base}/health")
    assert status == 200
    assert "status" in data


def test_pipeline_sync_requires_auth(api_server):
    base, api_key = api_server
    headers = {"Authorization": f"Bearer {api_key}"}
    status, data = _request(
        f"{base}/pipeline/run",
        method="POST",
        data={"input_text": "Contact a@b.com", "attest": False, "async": False},
        headers=headers,
    )
    assert status == 200
    assert data["result"]["final_status"] == "ATTESTED"


def test_pipeline_async_job(api_server):
    base, api_key = api_server
    headers = {"Authorization": f"Bearer {api_key}"}
    status, data = _request(
        f"{base}/pipeline/run",
        method="POST",
        data={"input_text": "hello@world.com", "attest": False, "async": True},
        headers=headers,
    )
    assert status == 202
    job_id = data["job_id"]

    for _ in range(30):
        _, job = _request(f"{base}/jobs/{job_id}", headers=headers)
        if job["status"] in ("completed", "failed"):
            break
        time.sleep(0.2)
    assert job["status"] == "completed"


def test_jobs_stream_includes_cors_for_tauri(api_server):
    base, api_key = api_server
    req = urllib.request.Request(
        f"{base}/api/v2/jobs/stream?seconds=2&poll_ms=250",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "text/event-stream",
            "Origin": "https://tauri.localhost",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "text/event-stream"
        assert resp.headers.get("Access-Control-Allow-Origin") == "https://tauri.localhost"