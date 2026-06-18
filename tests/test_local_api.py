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
    managed = tmp_path / "managed"
    for sub in ("config", "store", "audit", "rules", "workflows", "knowledge", "artifacts"):
        (managed / sub).mkdir(parents=True)

    for src, dst in [
        (ROOT / "managed" / "rules" / "rule1.md", managed / "rules" / "rule1.md"),
        (ROOT / "managed" / "workflows" / "workflow1.md", managed / "workflows" / "workflow1.md"),
        (ROOT / "managed" / "knowledge" / "knowledge1.md", managed / "knowledge" / "knowledge1.md"),
    ]:
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    legacy_policy = ROOT / "managed" / "config" / "capabilities.json.legacy"
    if legacy_policy.exists():
        (managed / "config" / "capabilities.json").write_text(
            legacy_policy.read_text(encoding="utf-8"), encoding="utf-8"
        )

    server = APXLocalServer(base_path=tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)
    host, port = server.address
    base = f"http://{host}:{port}"
    yield base, server.generated_key or "test"
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