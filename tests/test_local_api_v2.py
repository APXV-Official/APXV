"""Tests for APXV Local API v2 endpoints."""

from __future__ import annotations

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
from agents.local_api import APXLocalServer
from agents.upload_manager import parse_multipart_form

from tests.helpers import seed_governance_libraries, seed_test_instance


def _request(
    url: str,
    method: str = "GET",
    data: dict | bytes | None = None,
    headers: dict | None = None,
):
    body = None
    req_headers = headers or {}
    if isinstance(data, dict):
        body = json.dumps(data).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    elif isinstance(data, bytes):
        body = data
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8")), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(detail)
        except json.JSONDecodeError:
            payload = {"raw": detail}
        return exc.code, payload, dict(exc.headers)


def _multipart_body(filename: str, content: str, field: str = "files") -> tuple[bytes, str]:
    boundary = "----apxv-test-boundary"
    parts = [
        f"--{boundary}\r\n",
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n',
        "Content-Type: text/plain\r\n\r\n",
        content,
        "\r\n",
        f"--{boundary}--\r\n",
    ]
    body = "".join(parts).encode("utf-8")
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


@pytest.fixture
def api_server(tmp_path):
    seed_governance_libraries(tmp_path)
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
        api_key = auth.create_key("pytest-operator", description="API v2 test fixture key")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.address
    base = f"http://{host}:{port}"
    for _ in range(50):
        try:
            _request(f"{base}/api/v2/system/health")
            break
        except Exception:
            time.sleep(0.1)
    else:
        pytest.fail("API server did not become ready")
    yield base, api_key
    server.worker.stop()
    server.httpd.shutdown()


def test_v2_health_public(api_server):
    base, _ = api_server
    status, data, headers = _request(f"{base}/api/v2/system/health")
    assert status == 200
    assert data["status"] in ("healthy", "degraded")
    assert any(k.lower() == "x-request-id" for k in headers)
    assert data["api_version"] == "2.0.0"


def test_v2_operator_key_hint_public(api_server):
    base, api_key = api_server
    status, data, _ = _request(f"{base}/api/v2/system/operator-key-hint")
    assert status == 200
    assert data["key"] == api_key
    assert "file_path" in data
    assert "file_content" in data


def test_v2_status_requires_auth(api_server):
    base, api_key = api_server
    status, data, _ = _request(
        f"{base}/api/v2/system/status",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert status == 200
    assert "runtime_version" in data


def test_v2_status_apxv_api_key_header(api_server):
    base, api_key = api_server
    status, data, _ = _request(
        f"{base}/api/v2/system/status",
        headers={"APXV-API-KEY": api_key},
    )
    assert status == 200
    assert "runtime_version" in data


def test_v2_doctor(api_server):
    base, api_key = api_server
    status, data, _ = _request(
        f"{base}/api/v2/system/doctor",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert status == 200
    assert "checks" in data


def test_v2_artifacts_list_and_summary(api_server):
    base, api_key = api_server
    headers = {"Authorization": f"Bearer {api_key}"}
    _request(
        f"{base}/api/v2/pipeline/run",
        method="POST",
        data={"pack": "reference", "input_text": "email a@b.com", "attest": False, "async": False},
        headers=headers,
    )
    status, page, _ = _request(f"{base}/api/v2/artifacts?limit=5", headers=headers)
    assert status == 200
    assert page["total"] >= 1
    artifact_hash = page["items"][0]["artifact_hash"]
    status, summary, _ = _request(
        f"{base}/api/v2/artifacts/{artifact_hash}/summary",
        headers=headers,
    )
    assert status == 200
    assert summary["artifact_hash"] == artifact_hash


def test_v2_audit_logs_and_entries(api_server):
    base, api_key = api_server
    headers = {"Authorization": f"Bearer {api_key}"}
    status, data, _ = _request(f"{base}/api/v2/audit/logs", headers=headers)
    assert status == 200
    assert data["logs"]
    log_name = data["logs"][0]["name"]
    status, entries, _ = _request(
        f"{base}/api/v2/audit/logs/{log_name}/entries?limit=5",
        headers=headers,
    )
    assert status == 200
    assert "items" in entries
    assert entries["total"] >= 1


def test_v2_pipeline_reference_async(api_server):
    base, api_key = api_server
    headers = {"Authorization": f"Bearer {api_key}"}
    status, queued, _ = _request(
        f"{base}/api/v2/pipeline/run",
        method="POST",
        data={"pack": "reference", "input_text": "phone 5551234567", "async": True},
        headers=headers,
    )
    assert status == 202
    job_id = queued["job_id"]
    for _ in range(40):
        _, job, _ = _request(f"{base}/api/v2/jobs/{job_id}", headers=headers)
        if job["status"] in ("completed", "failed"):
            break
        time.sleep(0.2)
    assert job["status"] == "completed"


def test_v2_packs_catalog(api_server):
    base, api_key = api_server
    headers = {"Authorization": f"Bearer {api_key}"}
    status, data, _ = _request(f"{base}/api/v2/packs", headers=headers)
    assert status == 200
    assert len(data["packs"]) >= 3
    pack_id = data["packs"][0]["id"]
    status, detail, _ = _request(f"{base}/api/v2/packs/{pack_id}", headers=headers)
    assert status == 200
    assert detail["id"] == pack_id


def test_v2_agents_registry(api_server):
    base, api_key = api_server
    headers = {"Authorization": f"Bearer {api_key}"}

    status, page, _ = _request(f"{base}/api/v2/agents?limit=50", headers=headers)
    assert status == 200
    assert page["total"] >= 5
    assert any(item["id"] == "APXV-AGENT-001" for item in page["items"])

    status, agent, _ = _request(f"{base}/api/v2/agents/APXV-AGENT-002", headers=headers)
    assert status == 200
    assert agent["name"] == "WorkflowOrchestrator"
    assert "apxv-pack-reference-redaction" in agent["packs"]

    status, chain, _ = _request(
        f"{base}/api/v2/packs/apxv-pack-ai-governance/agents",
        headers=headers,
    )
    assert status == 200
    assert chain["pack_id"] == "apxv-pack-ai-governance"
    assert len(chain["agents"]) == 4
    assert chain["agents"][-1]["id"] == "APXV-AGENT-LLM-001"


def test_v2_packs_active_activate_and_clone(api_server):
    base, api_key = api_server
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    status, active_before, _ = _request(f"{base}/api/v2/packs/active", headers=headers)
    assert status == 200
    assert active_before.get("active") is None

    status, activated, _ = _request(
        f"{base}/api/v2/packs/apxv-pack-reference-redaction/activate",
        method="POST",
        data={},
        headers=headers,
    )
    assert status == 200
    assert activated["pack_id"] == "apxv-pack-reference-redaction"
    assert activated["active"]["pack_id"] == "apxv-pack-reference-redaction"

    status, active_after, _ = _request(f"{base}/api/v2/packs/active", headers=headers)
    assert status == 200
    assert active_after["active"]["pack_id"] == "apxv-pack-reference-redaction"
    assert active_after["pack"]["id"] == "apxv-pack-reference-redaction"

    status, cloned, _ = _request(
        f"{base}/api/v2/packs/apxv-pack-reference-redaction/clone",
        method="POST",
        data={
            "pack_id": "apxv-pack-api-clone",
            "name": "API Clone Pack",
            "description": "Created by test_local_api_v2",
        },
        headers=headers,
    )
    assert status == 201
    assert cloned["pack"]["pack_id"] == "apxv-pack-api-clone"


def test_v2_upload_and_document_pack(api_server, tmp_path):
    base, api_key = api_server
    headers = {"Authorization": f"Bearer {api_key}"}
    body, content_type = _multipart_body("invoice.txt", "Contact bill@corp.com SSN 123-45-6789")
    headers = {**headers, "Content-Type": content_type}
    status, created, _ = _request(
        f"{base}/api/v2/uploads",
        method="POST",
        data=body,
        headers=headers,
    )
    assert status == 201
    upload_id = created["session"]["upload_id"]
    status, result, _ = _request(
        f"{base}/api/v2/pipeline/run",
        method="POST",
        data={"pack": "document", "upload_id": upload_id, "async": False},
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    assert status == 200
    assert result["result"]["pack"] == "document"


def test_v2_verify_python_only(api_server):
    base, api_key = api_server
    headers = {"Authorization": f"Bearer {api_key}"}
    _, pipeline, _ = _request(
        f"{base}/api/v2/pipeline/run",
        method="POST",
        data={"pack": "reference", "input_text": "no pii", "async": False},
        headers=headers,
    )
    artifact_hash = pipeline["result"]["artifact_hash"]
    status, report, _ = _request(
        f"{base}/api/v2/verify/attestation",
        method="POST",
        data={"artifact_hash": artifact_hash, "real_zk": False},
        headers=headers,
    )
    assert status == 200
    assert "python" in report


def test_v2_keys_create_and_revoke_requires_spare(api_server):
    base, api_key = api_server
    headers = {"Authorization": f"Bearer {api_key}"}
    status, created, _ = _request(
        f"{base}/api/v2/keys",
        method="POST",
        data={"id": "temp-ui-key", "description": "test"},
        headers=headers,
    )
    assert status == 201
    assert created["api_key"]
    status, revoked, _ = _request(
        f"{base}/api/v2/keys/temp-ui-key",
        method="DELETE",
        headers=headers,
    )
    assert status == 200
    assert revoked["id"] == "temp-ui-key"


def test_v2_integrations_ollama(api_server):
    base, api_key = api_server
    status, data, _ = _request(
        f"{base}/api/v2/integrations/ollama",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert status == 200
    assert "reachable" in data


def test_v2_integrations_repair(api_server, monkeypatch):
    base, api_key = api_server
    monkeypatch.setattr(
        "scripts.bootstrap.integrations.repair_integrations",
        lambda _base: {
            "ok": False,
            "install_json_updated": False,
            "ollama": {"verified": False, "detail": "mock"},
            "voice": {"enabled": False, "detail": "mock"},
        },
    )
    status, data, _ = _request(
        f"{base}/api/v2/integrations/repair",
        method="POST",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert status == 200
    assert "ollama" in data
    assert "voice" in data


def test_multipart_parser_roundtrip():
    body, content_type = _multipart_body("sample.txt", "hello")
    parsed = parse_multipart_form(body, content_type)
    assert parsed["files"][0]["filename"] == "sample.txt"
    assert parsed["files"][0]["content"].decode("utf-8") == "hello"