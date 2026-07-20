"""API v2 composition pipeline endpoints."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

LINEAR = {
    "apiVersion": "apxv.pipeline/v0.1",
    "kind": "Pipeline",
    "id": "apxv-pipeline-api-linear",
    "name": "API linear",
    "version": "0.1.0",
    "steps": [
        {"id": "redact", "name": "R", "uses": "agent:APXV-AGENT-001"},
        {"id": "orchestrate", "name": "O", "uses": "agent:APXV-AGENT-002"},
        {"id": "decide", "name": "D", "uses": "agent:APXV-AGENT-003"},
    ],
}

SAMPLE = (
    "Contact John at john.doe@example.com or call (555) 123-4567. "
    "SSN: 123-45-6789. Card: 4111 1111 1111 1111."
)


def _req(url, method="GET", data=None, api_key=None):
    headers = {}
    body = None
    if api_key:
        headers["APXV-API-KEY"] = api_key
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        try:
            parsed = json.loads(payload)
        except Exception:
            parsed = {"raw": payload}
        return exc.code, parsed


def test_pipelines_validate_create_run(api_server):
    base, api_key, _tmp = api_server

    status, body = _req(
        f"{base}/api/v2/pipelines/validate",
        method="POST",
        data={"pipeline": LINEAR},
        api_key=api_key,
    )
    assert status == 200, body
    assert body["ok"] is True

    status, body = _req(
        f"{base}/api/v2/pipelines",
        method="POST",
        data={"pipeline": LINEAR, "format": "yaml"},
        api_key=api_key,
    )
    assert status == 201, body
    assert body["pipeline"]["id"] == "apxv-pipeline-api-linear"

    status, body = _req(f"{base}/api/v2/pipelines", api_key=api_key)
    assert status == 200
    assert any(p["id"] == "apxv-pipeline-api-linear" for p in body["pipelines"])

    status, body = _req(
        f"{base}/api/v2/pipelines/apxv-pipeline-api-linear/run",
        method="POST",
        data={"input_text": SAMPLE, "async": False},
        api_key=api_key,
    )
    assert status == 200, body
    result = body["result"]
    assert result["final_status"] == "succeeded"
    assert len(result["run_trace"]["steps"]) == 3

    status, body = _req(
        f"{base}/api/v2/pipelines/apxv-pipeline-api-linear/export?format=json",
        api_key=api_key,
    )
    assert status == 200
    assert "apxv-pipeline-api-linear" in body["content"]


def test_pipelines_validate_failure(api_server):
    base, api_key, _tmp = api_server
    status, body = _req(
        f"{base}/api/v2/pipelines/validate",
        method="POST",
        data={"pipeline": {"apiVersion": "nope", "kind": "Pipeline"}},
        api_key=api_key,
    )
    assert status == 400
    assert body["ok"] is False
    assert body["errors"]


def test_pipelines_templates_list(api_server):
    base, api_key, tmp = api_server
    # Seed example pipelines into isolated tree if missing
    examples = tmp / "examples" / "pipelines"
    if not examples.is_dir():
        import shutil
        from pathlib import Path

        src = Path(__file__).parent.parent / "examples" / "pipelines"
        if src.is_dir():
            shutil.copytree(src, examples)
    status, body = _req(f"{base}/api/v2/pipelines/templates", api_key=api_key)
    assert status == 200, body
    assert "templates" in body
    # When package root resolves, templates may come from package examples/
    # Isolated tmp may still list package examples via resolve_apxv_root
    assert isinstance(body["templates"], list)


def test_pipelines_templates_get_when_available(api_server):
    base, api_key, _tmp = api_server
    status, body = _req(f"{base}/api/v2/pipelines/templates", api_key=api_key)
    assert status == 200
    templates = body.get("templates") or []
    if not templates:
        return
    tid = templates[0]["id"]
    status, body = _req(
        f"{base}/api/v2/pipelines/templates/{tid}",
        api_key=api_key,
    )
    assert status == 200, body
    assert body.get("content")
    assert body.get("template", {}).get("maturity") == "Example"
