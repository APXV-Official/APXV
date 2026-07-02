"""Pytest hooks and fixtures."""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.auth import APIKeyAuth
from agents.local_api import APXLocalServer

from tests.helpers import seed_test_instance


def _api_request(url: str, method: str = "GET", data: dict | None = None, headers: dict | None = None):
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
    server_config_path = tmp_path / "managed" / "config" / "server.json"
    server_config = json.loads(server_config_path.read_text(encoding="utf-8"))
    server_config["port"] = 0
    server_config_path.write_text(json.dumps(server_config, indent=2), encoding="utf-8")
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
            _api_request(f"{base}/health")
            break
        except Exception:
            time.sleep(0.1)
    else:
        pytest.fail("API server did not become ready")
    yield base, api_key, tmp_path
    server.worker.stop()
    server.httpd.shutdown()


def pytest_ignore_collect(collection_path: Path, config):
    """Skip legacy reference trees without hard-coding vendor names in config."""
    name = collection_path.name
    if name.endswith("SDK v1.0.0") or name.endswith("-proof-system"):
        return True
    if name == "legacy":
        return True
    return None