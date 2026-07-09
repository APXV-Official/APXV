"""
APXV — Local HTTP API (Phase 4 / Step 1)

Stdlib-only HTTP server bound to localhost.
Air-gapped: no outbound network, no external dependencies.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import json
import threading
import time
import traceback

from .api_v2 import ApiV2Router
from .auth import APIKeyAuth
from .cors import CORS_ALLOW_HEADERS, CORS_ALLOW_METHODS, resolve_cors_origin
from .env import get_env
from .backup_restore import BackupRestoreError
from .governance_approval import GovernanceApprovalError
from .job_queue import JobQueue
from .pipeline_service import execute_job_payload
from .runtime import APXVRuntime


DEFAULT_SERVER_CONFIG = {
    "bind_address": "127.0.0.1",
    "port": 8741,
    "require_auth": True,
    "max_job_retries": 1,
    "worker_poll_seconds": 1.0,
}

LOCALHOST_BIND_ADDRESSES = frozenset({"127.0.0.1", "localhost", "::1"})


def validate_localhost_bind(bind_address: str) -> str:
    """Reject non-localhost binds — APX local API is air-gap safe by design."""
    normalized = bind_address.strip().lower()
    allowed = set(LOCALHOST_BIND_ADDRESSES)
    if get_env("APXV_CONTAINER_BIND") == "1":
        allowed.add("0.0.0.0")
    if normalized not in allowed:
        raise ValueError(
            f"APX local API must bind to localhost only (got {bind_address!r}). "
            f"Allowed: {', '.join(sorted(allowed))}"
        )
    return bind_address


class JobWorker:
    """Background worker that processes queued pipeline jobs."""

    def __init__(
        self,
        queue: JobQueue,
        runtime: APXVRuntime,
        max_retries: int = 1,
        poll_seconds: float = 1.0,
    ):
        self.queue = queue
        self.runtime = runtime
        self.max_retries = max_retries
        self.poll_seconds = poll_seconds
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True, name="apx-job-worker")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.is_set():
            job = self.queue.claim_next("pipeline")
            if not job:
                time.sleep(self.poll_seconds)
                continue
            try:
                result = execute_job_payload(job["payload"], runtime=self.runtime)
                self.queue.complete(job["id"], result)
            except Exception as exc:
                retries = job.get("retry_count", 0)
                if retries < self.max_retries:
                    self.queue.fail(job["id"], str(exc), retry=True)
                else:
                    self.queue.fail(job["id"], traceback.format_exc()[-2000:], retry=False)
            time.sleep(0.05)


def _load_server_config(base_path: Path) -> Dict[str, Any]:
    path = base_path / "managed" / "config" / "server.json"
    if not path.exists():
        config = DEFAULT_SERVER_CONFIG.copy()
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return config
    return {**DEFAULT_SERVER_CONFIG, **json.loads(path.read_text(encoding="utf-8"))}


def create_handler(
    runtime: APXVRuntime,
    auth: APIKeyAuth,
    queue: JobQueue,
    server_config: Dict[str, Any],
):
    handler_runtime = runtime
    handler_auth = auth
    handler_queue = queue
    handler_require_auth = server_config.get("require_auth", True)

    class APXVHandler(BaseHTTPRequestHandler):
        runtime = handler_runtime
        auth = handler_auth
        queue = handler_queue
        require_auth = handler_require_auth

        def log_message(self, format: str, *args) -> None:
            self.runtime.system_audit.log_event(
                event_type="api_request",
                data={"client": self.client_address[0], "message": format % args},
            )

        def _read_json(self) -> Dict[str, Any]:
            length = int(self.headers.get("Content-Length", 0))
            if length == 0:
                return {}
            body = self.rfile.read(length)
            return json.loads(body.decode("utf-8"))

        def _headers_dict(self) -> Dict[str, str]:
            return {k: v for k, v in self.headers.items()}

        def _check_auth(self) -> bool:
            if not self.require_auth:
                return True
            key = self.auth.extract_key_from_headers(self._headers_dict())
            return self.auth.validate(key)

        def _send(self, status: int, payload: Dict[str, Any]) -> None:
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Deprecation", "true")
            self.send_header("Sunset", "v1.4")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header(
                "Access-Control-Allow-Origin",
                resolve_cors_origin(self.headers.get("Origin", "")),
            )
            self.send_header("Access-Control-Allow-Methods", CORS_ALLOW_METHODS)
            self.send_header("Access-Control-Allow-Headers", CORS_ALLOW_HEADERS)
            self.end_headers()
            self.wfile.write(body)

        def _unauthorized(self) -> None:
            self._send(401, {"error": "unauthorized", "message": "Valid API key required"})

        def _not_found(self) -> None:
            self._send(404, {"error": "not_found"})

        def _dispatch_v2(self, method: str) -> bool:
            return ApiV2Router(self).dispatch(method)

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.send_header(
                "Access-Control-Allow-Origin",
                resolve_cors_origin(self.headers.get("Origin", "")),
            )
            self.send_header("Access-Control-Allow-Methods", CORS_ALLOW_METHODS)
            self.send_header("Access-Control-Allow-Headers", CORS_ALLOW_HEADERS)
            self.send_header("Access-Control-Max-Age", "86400")
            self.end_headers()

        def do_GET(self) -> None:
            if self._dispatch_v2("GET"):
                return

            path = self.path.split("?", 1)[0]

            if path == "/health":
                integrity = self.runtime.verify_integrity()
                self._send(
                    200,
                    {
                        "status": "healthy" if integrity["healthy"] else "degraded",
                        "air_gapped": True,
                        "sovereign_setup": integrity.get("sovereign_setup", False),
                        "integrity": integrity,
                    },
                )
                return

            if not self._check_auth():
                self._unauthorized()
                return

            if path == "/governance":
                self._send(200, self.runtime.governance.get_status())
                return

            if path == "/governance/proposals":
                proposals = self.runtime.governance.list_proposals(limit=50)
                self._send(200, {"proposals": proposals})
                return

            if path.startswith("/governance/proposals/"):
                proposal_id = path.split("/governance/proposals/", 1)[1].strip("/")
                if "/" in proposal_id:
                    self._not_found()
                    return
                proposal = self.runtime.governance.get_proposal(proposal_id)
                if not proposal:
                    self._not_found()
                    return
                self._send(200, proposal)
                return

            if path == "/capabilities":
                self._send(200, self.runtime.capability_checker.get_status())
                return

            if path == "/backups":
                backups = self.runtime.backup_manager.list_backups()
                self._send(200, {"backups": backups})
                return

            if path == "/status":
                self._send(200, self.runtime.get_status())
                return

            if path == "/jobs":
                jobs = self.queue.list_jobs(limit=20)
                self._send(200, {"jobs": jobs})
                return

            if path.startswith("/jobs/"):
                job_id = path.split("/jobs/", 1)[1].strip("/")
                job = self.queue.get(job_id)
                if not job:
                    self._not_found()
                    return
                self._send(200, job)
                return

            if path.startswith("/artifacts/"):
                artifact_id = path.split("/artifacts/", 1)[1].strip("/")
                try:
                    data = self.runtime.provider.read_artifact(artifact_id)
                    self._send(200, data)
                except FileNotFoundError:
                    self._not_found()
                except ValueError as exc:
                    self._send(500, {"error": "integrity_failed", "message": str(exc)})
                return

            self._not_found()

        def do_POST(self) -> None:
            if self._dispatch_v2("POST"):
                return

            if not self._check_auth():
                self._unauthorized()
                return

            path = self.path.split("?", 1)[0]
            body = self._read_json()

            if path == "/backup/create":
                try:
                    result = self.runtime.backup_manager.create_backup()
                    self._send(201, {"message": "backup created", **result})
                except BackupRestoreError as exc:
                    self._send(500, {"error": "backup_failed", "message": str(exc)})
                return

            if path == "/backup/restore":
                archive_name = body.get("filename") or body.get("archive")
                if not archive_name:
                    self._send(400, {"error": "missing_filename"})
                    return
                archive_path = self.runtime.backup_manager.backup_dir / Path(archive_name).name
                try:
                    result = self.runtime.backup_manager.restore_backup(
                        archive_path,
                        dry_run=bool(body.get("dry_run", False)),
                        create_safety_backup=not bool(body.get("no_safety_backup", False)),
                    )
                    self._send(200, {"message": "backup restored", **result})
                except BackupRestoreError as exc:
                    self._send(400, {"error": "restore_failed", "message": str(exc)})
                return

            if path == "/governance/proposals":
                try:
                    result = self.runtime.governance.propose_change(
                        spec_type=body.get("spec_type", ""),
                        content=body.get("content", ""),
                        proposed_by=body.get("proposed_by", "api-operator"),
                        summary=body.get("summary", ""),
                    )
                    self._send(201, {"message": "proposal created", "proposal": result})
                except (GovernanceApprovalError, ValueError) as exc:
                    self._send(400, {"error": "proposal_failed", "message": str(exc)})
                return

            if path.startswith("/governance/proposals/"):
                parts = path.split("/governance/proposals/", 1)[1].strip("/").split("/")
                if len(parts) != 2:
                    self._not_found()
                    return
                proposal_id, action = parts
                governance = self.runtime.governance
                try:
                    if action == "approve":
                        result = governance.approve_proposal(
                            proposal_id,
                            approved_by=body.get("approved_by", "api-operator"),
                        )
                        self._send(200, {"message": "proposal approved", **result})
                        return
                    if action == "reject":
                        result = governance.reject_proposal(
                            proposal_id,
                            rejected_by=body.get("rejected_by", "api-operator"),
                            reason=body.get("reason", ""),
                        )
                        self._send(200, {"message": "proposal rejected", "proposal": result})
                        return
                    if action == "apply":
                        result = governance.apply_proposal(proposal_id)
                        self._send(200, {"message": "proposal applied", "proposal": result})
                        return
                except GovernanceApprovalError as exc:
                    self._send(400, {"error": "governance_action_failed", "message": str(exc)})
                    return
                self._not_found()
                return

            if path != "/pipeline/run":
                self._not_found()
                return

            input_text = body.get("input_text")
            attest = bool(body.get("attest", False))
            run_async = body.get("async", True)

            payload = {"input_text": input_text, "attest": attest}

            if run_async:
                job = self.queue.enqueue("pipeline", payload)
                self._send(202, {"message": "job queued", **job})
                return

            try:
                result = execute_job_payload(payload, runtime=self.runtime)
                self._send(200, {"message": "pipeline complete", "result": result})
            except Exception as exc:
                self._send(500, {"error": "pipeline_failed", "message": str(exc)})

        def do_DELETE(self) -> None:
            if self._dispatch_v2("DELETE"):
                return
            self._not_found()

    return APXVHandler


class APXVLocalServer:
    """Local governed API server."""

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent
        self.runtime = APXVRuntime(base_path=self.base_path)
        self.config = _load_server_config(self.base_path)

        config_dir = self.base_path / "managed" / "config"
        self.auth = APIKeyAuth(config_dir / "api_keys.json")
        self.generated_key = self.auth.ensure_default_key()

        jobs_db = self.base_path / "managed" / "store" / "jobs.db"
        self.queue = JobQueue(jobs_db)

        handler = create_handler(self.runtime, self.auth, self.queue, self.config)
        bind = validate_localhost_bind(self.config.get("bind_address", "127.0.0.1"))
        port = int(self.config.get("port", 8741))
        self.httpd = ThreadingHTTPServer((bind, port), handler)
        if port == 0:
            _, assigned = self.httpd.server_address
            self.config["port"] = assigned

        self.worker = JobWorker(
            queue=self.queue,
            runtime=self.runtime,
            max_retries=int(self.config.get("max_job_retries", 1)),
            poll_seconds=float(self.config.get("worker_poll_seconds", 1.0)),
        )

    @property
    def address(self) -> Tuple[str, int]:
        host, port = self.httpd.server_address
        return host, port

    def serve_forever(self) -> None:
        self.worker.start()
        self.runtime.system_audit.log_event(
            event_type="api_server_started",
            data={"bind": self.address[0], "port": self.address[1]},
        )
        try:
            self.httpd.serve_forever()
        finally:
            self.worker.stop()
            self.httpd.server_close()


# v1.3.x compat — removed in v1.4
APXLocalServer = APXVLocalServer