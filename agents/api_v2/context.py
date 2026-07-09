"""HTTP context helpers for API v2."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse
import json
import uuid

from ..auth import APIKeyAuth
from ..cors import CORS_ALLOW_HEADERS, resolve_cors_origin
from ..job_queue import JobQueue
from ..runtime import APXRuntime
from ..upload_manager import UploadManager


class ApiV2Context:
    def __init__(
        self,
        handler: BaseHTTPRequestHandler,
        *,
        runtime: APXRuntime,
        auth: APIKeyAuth,
        queue: JobQueue,
        require_auth: bool,
    ):
        self.handler = handler
        self.runtime = runtime
        self.auth = auth
        self.queue = queue
        self.require_auth = require_auth
        self.uploads = UploadManager(runtime.base_path)
        self.request_id = f"req-{uuid.uuid4().hex[:12]}"

    def path_and_query(self) -> Tuple[str, Dict[str, str]]:
        parsed = urlparse(self.handler.path)
        path = parsed.path.rstrip("/") or "/"
        query: Dict[str, str] = {}
        for key, values in parse_qs(parsed.query).items():
            if values:
                query[key] = values[-1]
        return path, query

    def check_auth(self) -> bool:
        if not self.require_auth:
            return True
        key = self.auth.extract_key_from_headers(
            {k: v for k, v in self.handler.headers.items()}
        )
        return self.auth.validate(key)

    def read_json(self) -> Dict[str, Any]:
        length = int(self.handler.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        body = self.handler.rfile.read(length)
        return json.loads(body.decode("utf-8"))

    def read_raw_body(self) -> bytes:
        length = int(self.handler.headers.get("Content-Length", 0))
        if length == 0:
            return b""
        return self.handler.rfile.read(length)

    def send_json(
        self,
        status: int,
        payload: Dict[str, Any],
        *,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        body = json.dumps(payload, indent=2, default=str).encode("utf-8")
        self.handler.send_response(status)
        self.handler.send_header("Content-Type", "application/json")
        self.handler.send_header("Content-Length", str(len(body)))
        self.handler.send_header("X-Request-Id", self.request_id)
        self.handler.send_header(
            "Access-Control-Allow-Origin",
            resolve_cors_origin(self.handler.headers.get("Origin", "")),
        )
        self.handler.send_header("Access-Control-Allow-Headers", CORS_ALLOW_HEADERS)
        if extra_headers:
            for key, value in extra_headers.items():
                self.handler.send_header(key, value)
        self.handler.end_headers()
        self.handler.wfile.write(body)

    def send_error(
        self,
        status: int,
        error: str,
        message: str,
        *,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload: Dict[str, Any] = {"error": error, "message": message}
        if details:
            payload["details"] = details
        self.send_json(status, payload)

    def unauthorized(self) -> None:
        self.send_error(401, "unauthorized", "Valid API key required")

    def not_found(self) -> None:
        self.send_error(404, "not_found", "Resource not found")

    @staticmethod
    def paginate(items: list, *, total: int, limit: int, offset: int) -> Dict[str, Any]:
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def parse_int(value: Optional[str], default: int, *, minimum: int = 0, maximum: int = 200) -> int:
        try:
            parsed = int(value) if value is not None else default
        except (TypeError, ValueError):
            parsed = default
        return max(minimum, min(maximum, parsed))