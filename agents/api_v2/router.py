"""API v2 route dispatch for APXV local API v2."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import json
import re
import time

from ..backup_restore import BackupRestoreError
from ..governance_approval import GovernanceApprovalError
from ..pack_catalog import get_pack, list_packs
from ..agent_registry import agents_for_pack, get_agent, list_agents
from ..pack_install import (
    PackInstallError,
    activate_pack,
    clone_pack,
    get_active_pack_summary,
)
from ..pack_scaffold import create_pack
from ..pipeline_service import execute_job_payload, run_pipeline_quiet
from ..studio_service import (
    StudioError,
    get_studio_pack,
    list_operator_agents,
    list_promoted_for_workbench,
    list_studio_packs,
    load_operator_agent,
    promote_agent,
    promote_pack,
    save_operator_agent,
    save_studio_pack,
    run_operator_agent_test,
    run_studio_pack_test,
)
from ..proof_studio import (
    export_proof_claim_bundle,
    get_proof_profile,
    list_predicate_catalog,
    list_proof_profiles,
    list_proof_templates,
    promote_proof_profile,
    run_proof_profile_test,
    save_from_template,
    save_profile_from_intent,
    save_proof_profile,
    universal_keys_available,
)
from ..proof_intent import compile_intent
from ..upload_manager import parse_multipart_form
from ..verification_service import load_attested_for_verify, verify_attestation_artifact
from .context import ApiV2Context

HandlerFn = Callable[[ApiV2Context, Dict[str, str], Dict[str, str]], bool]


class ApiV2Router:
    PUBLIC_PATHS = frozenset(
        {
            "/api/v2/system/health",
            "/api/v2/system/operator-key-hint",
        }
    )

    def __init__(self, handler):
        self.ctx = ApiV2Context(
            handler,
            runtime=handler.runtime,
            auth=handler.auth,
            queue=handler.queue,
            require_auth=handler.require_auth,
        )

    def dispatch(self, method: str) -> bool:
        path, query = self.ctx.path_and_query()
        if not path.startswith("/api/v2"):
            return False

        if path not in self.PUBLIC_PATHS and not self.ctx.check_auth():
            self.ctx.unauthorized()
            return True

        params = self._match(method.upper(), path)
        if params is None:
            self.ctx.not_found()
            return True

        routes = self._routes()
        key = (method.upper(), params["route"])
        handler_fn = routes.get(key)
        if not handler_fn:
            self.ctx.send_error(405, "method_not_allowed", f"{method} not supported for {path}")
            return True

        return handler_fn(self.ctx, query, params)

    def _match(self, method: str, path: str) -> Optional[Dict[str, str]]:
        patterns: List[Tuple[str, str, str]] = [
            ("GET", r"^/api/v2/system/health$", "system.health"),
            ("GET", r"^/api/v2/system/operator-key-hint$", "system.operator_key_hint"),
            ("GET", r"^/api/v2/system/status$", "system.status"),
            ("GET", r"^/api/v2/system/doctor$", "system.doctor"),
            ("POST", r"^/api/v2/system/integrity$", "system.integrity"),
            ("POST", r"^/api/v2/system/repair-audit$", "system.repair_audit"),
            ("GET", r"^/api/v2/system/verifier-bundle$", "system.verifier_bundle"),
            ("GET", r"^/api/v2/artifacts$", "artifacts.list"),
            ("GET", r"^/api/v2/artifacts/(?P<hash>[^/]+)/summary$", "artifacts.summary"),
            ("GET", r"^/api/v2/artifacts/(?P<hash>[^/]+)$", "artifacts.get"),
            ("GET", r"^/api/v2/audit/logs$", "audit.logs"),
            ("GET", r"^/api/v2/audit/logs/(?P<name>[^/]+)/entries$", "audit.entries"),
            ("GET", r"^/api/v2/jobs/stream$", "jobs.stream"),
            ("GET", r"^/api/v2/jobs/(?P<id>[^/]+)$", "jobs.get"),
            ("GET", r"^/api/v2/jobs$", "jobs.list"),
            ("POST", r"^/api/v2/pipeline/run$", "pipeline.run"),
            ("GET", r"^/api/v2/pipelines$", "pipelines.list"),
            ("POST", r"^/api/v2/pipelines$", "pipelines.create"),
            ("POST", r"^/api/v2/pipelines/validate$", "pipelines.validate"),
            ("POST", r"^/api/v2/pipelines/import$", "pipelines.import"),
            ("GET", r"^/api/v2/pipelines/templates$", "pipelines.templates.list"),
            (
                "GET",
                r"^/api/v2/pipelines/templates/(?P<id>[^/]+)$",
                "pipelines.templates.get",
            ),
            ("GET", r"^/api/v2/pipelines/(?P<id>[^/]+)/export$", "pipelines.export"),
            ("POST", r"^/api/v2/pipelines/(?P<id>[^/]+)/run$", "pipelines.run"),
            ("GET", r"^/api/v2/pipelines/(?P<id>[^/]+)$", "pipelines.get"),
            ("DELETE", r"^/api/v2/pipelines/(?P<id>[^/]+)$", "pipelines.delete"),
            (
                "POST",
                r"^/api/v2/jobs/(?P<id>[^/]+)/approve$",
                "jobs.approve",
            ),
            ("GET", r"^/api/v2/catalog/lint$", "catalog.lint"),
            ("POST", r"^/api/v2/catalog/smoke$", "catalog.smoke"),
            ("GET", r"^/api/v2/swarms$", "swarms.list"),
            ("POST", r"^/api/v2/swarms/run$", "swarms.run"),
            ("GET", r"^/api/v2/swarms/(?P<id>[^/]+)$", "swarms.get"),
            ("GET", r"^/api/v2/packs$", "packs.list"),
            ("POST", r"^/api/v2/packs$", "packs.create"),
            ("GET", r"^/api/v2/packs/active$", "packs.active"),
            ("POST", r"^/api/v2/packs/(?P<id>[^/]+)/activate$", "packs.activate"),
            ("POST", r"^/api/v2/packs/(?P<id>[^/]+)/clone$", "packs.clone"),
            ("GET", r"^/api/v2/packs/(?P<id>[^/]+)/agents$", "packs.agents"),
            ("GET", r"^/api/v2/packs/(?P<id>[^/]+)$", "packs.get"),
            ("GET", r"^/api/v2/agents$", "agents.list"),
            ("GET", r"^/api/v2/agents/(?P<id>[^/]+)$", "agents.get"),
            ("GET", r"^/api/v2/studio/agents$", "studio.agents.list"),
            ("POST", r"^/api/v2/studio/agents$", "studio.agents.save"),
            ("GET", r"^/api/v2/studio/agents/(?P<id>[^/]+)$", "studio.agents.get"),
            ("POST", r"^/api/v2/studio/agents/(?P<id>[^/]+)/test$", "studio.agents.test"),
            ("POST", r"^/api/v2/studio/agents/(?P<id>[^/]+)/promote$", "studio.agents.promote"),
            ("GET", r"^/api/v2/studio/packs$", "studio.packs.list"),
            ("POST", r"^/api/v2/studio/packs$", "studio.packs.save"),
            ("GET", r"^/api/v2/studio/packs/(?P<id>[^/]+)$", "studio.packs.get"),
            ("POST", r"^/api/v2/studio/packs/(?P<id>[^/]+)/test$", "studio.packs.test"),
            ("POST", r"^/api/v2/studio/packs/(?P<id>[^/]+)/promote$", "studio.packs.promote"),
            ("GET", r"^/api/v2/studio/proofs$", "studio.proofs.list"),
            ("POST", r"^/api/v2/studio/proofs$", "studio.proofs.save"),
            ("GET", r"^/api/v2/studio/proofs/catalog$", "studio.proofs.catalog"),
            ("GET", r"^/api/v2/studio/proofs/templates$", "studio.proofs.templates"),
            ("POST", r"^/api/v2/studio/proofs/from-template$", "studio.proofs.from_template"),
            ("POST", r"^/api/v2/studio/proofs/compile-intent$", "studio.proofs.compile_intent"),
            ("POST", r"^/api/v2/studio/proofs/from-intent$", "studio.proofs.from_intent"),
            ("GET", r"^/api/v2/studio/proofs/status$", "studio.proofs.status"),
            ("POST", r"^/api/v2/studio/proofs/export-claim$", "studio.proofs.export_claim"),
            ("GET", r"^/api/v2/studio/proofs/(?P<id>[^/]+)$", "studio.proofs.get"),
            ("POST", r"^/api/v2/studio/proofs/(?P<id>[^/]+)/test$", "studio.proofs.test"),
            ("POST", r"^/api/v2/studio/proofs/(?P<id>[^/]+)/promote$", "studio.proofs.promote"),
            ("GET", r"^/api/v2/studio/shelf$", "studio.shelf"),
            ("GET", r"^/api/v2/governance/specs$", "governance.specs"),
            ("GET", r"^/api/v2/governance/proposals$", "governance.proposals.list"),
            ("GET", r"^/api/v2/governance/proposals/(?P<proposal_id>[^/]+)$", "governance.proposals.get"),
            ("POST", r"^/api/v2/governance/proposals$", "governance.proposals.create"),
            (
                "POST",
                r"^/api/v2/governance/proposals/(?P<proposal_id>[^/]+)/(?P<action>approve|reject|apply)$",
                "governance.proposals.action",
            ),
            ("GET", r"^/api/v2/capabilities$", "capabilities.get"),
            ("GET", r"^/api/v2/backups$", "backups.list"),
            ("POST", r"^/api/v2/backups$", "backups.create"),
            ("POST", r"^/api/v2/backups/restore$", "backups.restore"),
            ("GET", r"^/api/v2/keys$", "keys.list"),
            ("POST", r"^/api/v2/keys$", "keys.create"),
            ("DELETE", r"^/api/v2/keys/(?P<id>[^/]+)$", "keys.delete"),
            ("POST", r"^/api/v2/verify/attestation$", "verify.attestation"),
            ("GET", r"^/api/v2/integrations/ollama$", "integrations.ollama"),
            ("POST", r"^/api/v2/integrations/repair$", "integrations.repair"),
            ("POST", r"^/api/v2/uploads$", "uploads.create"),
            ("GET", r"^/api/v2/uploads/(?P<id>[^/]+)$", "uploads.get"),
            ("DELETE", r"^/api/v2/uploads/(?P<id>[^/]+)$", "uploads.delete"),
        ]

        for route_method, pattern, route in patterns:
            if route_method != method:
                continue
            match = re.match(pattern, path)
            if not match:
                continue
            result = {"route": route}
            result.update({k: v for k, v in match.groupdict().items() if v is not None})
            return result
        return None

    def _routes(self) -> Dict[Tuple[str, str], HandlerFn]:
        return {
            ("GET", "system.health"): _system_health,
            ("GET", "system.operator_key_hint"): _system_operator_key_hint,
            ("GET", "system.status"): _system_status,
            ("GET", "system.doctor"): _system_doctor,
            ("POST", "system.integrity"): _system_integrity,
            ("POST", "system.repair_audit"): _system_repair_audit,
            ("GET", "system.verifier_bundle"): _system_verifier_bundle,
            ("GET", "artifacts.list"): _artifacts_list,
            ("GET", "artifacts.get"): _artifacts_get,
            ("GET", "artifacts.summary"): _artifacts_summary,
            ("GET", "audit.logs"): _audit_logs,
            ("GET", "audit.entries"): _audit_entries,
            ("GET", "jobs.list"): _jobs_list,
            ("GET", "jobs.get"): _jobs_get,
            ("GET", "jobs.stream"): _jobs_stream,
            ("POST", "pipeline.run"): _pipeline_run,
            ("GET", "pipelines.list"): _pipelines_list,
            ("POST", "pipelines.create"): _pipelines_create,
            ("POST", "pipelines.validate"): _pipelines_validate,
            ("POST", "pipelines.import"): _pipelines_import,
            ("GET", "pipelines.templates.list"): _pipelines_templates_list,
            ("GET", "pipelines.templates.get"): _pipelines_templates_get,
            ("GET", "pipelines.export"): _pipelines_export,
            ("POST", "pipelines.run"): _pipelines_run,
            ("GET", "pipelines.get"): _pipelines_get,
            ("DELETE", "pipelines.delete"): _pipelines_delete,
            ("POST", "jobs.approve"): _jobs_approve,
            ("GET", "catalog.lint"): _catalog_lint,
            ("POST", "catalog.smoke"): _catalog_smoke,
            ("GET", "swarms.list"): _swarms_list,
            ("POST", "swarms.run"): _swarms_run,
            ("GET", "swarms.get"): _swarms_get,
            ("GET", "packs.list"): _packs_list,
            ("POST", "packs.create"): _packs_create,
            ("GET", "packs.active"): _packs_active,
            ("POST", "packs.activate"): _packs_activate,
            ("POST", "packs.clone"): _packs_clone,
            ("GET", "packs.agents"): _packs_agents,
            ("GET", "packs.get"): _packs_get,
            ("GET", "agents.list"): _agents_list,
            ("GET", "agents.get"): _agents_get,
            ("GET", "studio.agents.list"): _studio_agents_list,
            ("POST", "studio.agents.save"): _studio_agents_save,
            ("GET", "studio.agents.get"): _studio_agents_get,
            ("POST", "studio.agents.test"): _studio_agents_test,
            ("POST", "studio.agents.promote"): _studio_agents_promote,
            ("GET", "studio.packs.list"): _studio_packs_list,
            ("POST", "studio.packs.save"): _studio_packs_save,
            ("GET", "studio.packs.get"): _studio_packs_get,
            ("POST", "studio.packs.test"): _studio_packs_test,
            ("POST", "studio.packs.promote"): _studio_packs_promote,
            ("GET", "studio.proofs.list"): _studio_proofs_list,
            ("POST", "studio.proofs.save"): _studio_proofs_save,
            ("GET", "studio.proofs.catalog"): _studio_proofs_catalog,
            ("GET", "studio.proofs.templates"): _studio_proofs_templates,
            ("POST", "studio.proofs.from_template"): _studio_proofs_from_template,
            ("POST", "studio.proofs.compile_intent"): _studio_proofs_compile_intent,
            ("POST", "studio.proofs.from_intent"): _studio_proofs_from_intent,
            ("GET", "studio.proofs.status"): _studio_proofs_status,
            ("POST", "studio.proofs.export_claim"): _studio_proofs_export_claim,
            ("GET", "studio.proofs.get"): _studio_proofs_get,
            ("POST", "studio.proofs.test"): _studio_proofs_test,
            ("POST", "studio.proofs.promote"): _studio_proofs_promote,
            ("GET", "studio.shelf"): _studio_shelf,
            ("GET", "governance.specs"): _governance_specs,
            ("GET", "governance.proposals.list"): _governance_proposals_list,
            ("GET", "governance.proposals.get"): _governance_proposals_get,
            ("POST", "governance.proposals.create"): _governance_proposals_create,
            ("POST", "governance.proposals.action"): _governance_proposals_action,
            ("GET", "capabilities.get"): _capabilities_get,
            ("GET", "backups.list"): _backups_list,
            ("POST", "backups.create"): _backups_create,
            ("POST", "backups.restore"): _backups_restore,
            ("GET", "keys.list"): _keys_list,
            ("POST", "keys.create"): _keys_create,
            ("DELETE", "keys.delete"): _keys_delete,
            ("POST", "verify.attestation"): _verify_attestation,
            ("GET", "integrations.ollama"): _integrations_ollama,
            ("POST", "integrations.repair"): _integrations_repair,
            ("POST", "uploads.create"): _uploads_create,
            ("GET", "uploads.get"): _uploads_get,
            ("DELETE", "uploads.delete"): _uploads_delete,
        }


def _load_operator_key_hint(base_path: Path) -> Dict[str, Any]:
    config_dir = base_path / "managed" / "config"
    if not config_dir.is_dir():
        raise FileNotFoundError(
            f"No OPERATOR-KEY-*.txt found under {config_dir} — run onboard or setup first."
        )

    for path in sorted(config_dir.glob("OPERATOR-KEY-*.txt")):
        file_content = path.read_text(encoding="utf-8")
        for line in file_content.splitlines():
            trimmed = line.strip()
            if trimmed.startswith("API Key:"):
                key = trimmed.split(":", 1)[1].strip()
                if key:
                    stem = path.stem
                    key_id = (
                        stem.removeprefix("OPERATOR-KEY-")
                        if stem.startswith("OPERATOR-KEY-")
                        else None
                    )
                    return {
                        "key": key,
                        "file_path": str(path),
                        "file_content": file_content,
                        "key_id": key_id,
                    }

    raise FileNotFoundError(
        f"No OPERATOR-KEY-*.txt found under {config_dir} — run onboard or setup first."
    )


def _system_operator_key_hint(
    ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]
) -> bool:
    try:
        ctx.send_json(200, _load_operator_key_hint(ctx.runtime.base_path))
    except FileNotFoundError as exc:
        ctx.send_error(404, "not_found", str(exc))
    return True


def _system_health(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    integrity = ctx.runtime.verify_integrity()
    ctx.send_json(
        200,
        {
            "status": "healthy" if integrity["healthy"] else "degraded",
            "air_gapped": True,
            "sovereign_setup": integrity.get("sovereign_setup", False),
            "integrity": integrity,
            "api_version": "2.0.0",
        },
    )
    return True


def _system_status(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    ctx.send_json(200, ctx.runtime.get_status())
    return True


def _system_doctor(ctx: ApiV2Context, query: Dict[str, str], _params: Dict[str, str]) -> bool:
    from scripts.apxv_doctor import run_doctor

    check_llm = query.get("check_llm", "").lower() in {"1", "true", "yes"}
    report = run_doctor(ctx.runtime.base_path, check_llm=check_llm)
    ctx.send_json(200, report)
    return True


def _system_integrity(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    result = ctx.runtime.verify_integrity()
    ctx.send_json(200, result)
    return True


def _system_repair_audit(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    result = ctx.runtime.repair_audit_logs()
    integrity = ctx.runtime.verify_integrity()
    ctx.send_json(
        200,
        {
            "message": "audit repair complete",
            "repair": result,
            "integrity": integrity,
        },
    )
    return True


def _system_verifier_bundle(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    base = ctx.runtime.base_path
    payload: Dict[str, Any] = {
        "bundle_version": "1.0.0",
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "governance": {"circuits": [], "manifest": None},
        "entity": {"circuits": [], "manifest": None},
        "includes_transcript": False,
    }
    gov_dir = base / "rust" / "apxv-circuits" / "keys"
    ent_dir = base / "rust" / "apxv-zk" / "keys"
    gov_manifest = gov_dir / "manifest.json"
    ent_manifest = ent_dir / "entity-manifest.json"
    if gov_manifest.exists():
        payload["governance"]["manifest"] = json.loads(gov_manifest.read_text(encoding="utf-8"))
        payload["governance"]["circuits"] = sorted(p.stem for p in gov_dir.glob("*.vk"))
    if ent_manifest.exists():
        payload["entity"]["manifest"] = json.loads(ent_manifest.read_text(encoding="utf-8"))
        payload["entity"]["circuits"] = sorted(p.stem for p in ent_dir.glob("*.vk"))
    transcript = base / "managed" / "config" / "ceremony-transcript.json"
    if transcript.exists():
        payload["includes_transcript"] = True
        payload["ceremony_transcript"] = json.loads(transcript.read_text(encoding="utf-8"))
    ctx.send_json(200, payload)
    return True


def _artifacts_list(ctx: ApiV2Context, query: Dict[str, str], _params: Dict[str, str]) -> bool:
    limit = ctx.parse_int(query.get("limit"), 50)
    offset = ctx.parse_int(query.get("offset"), 0, maximum=10_000)
    name_prefix = query.get("name_prefix")
    store = ctx.runtime.store
    total = store.count_artifacts(name_prefix=name_prefix or None)
    rows = store.list_artifacts(name_prefix=name_prefix or None, limit=limit, offset=offset)
    items = [
        {
            "artifact_hash": row["artifact_hash"],
            "name": row["name"],
            "written_at": row["written_at"],
            "blob_relpath": row["blob_relpath"],
            "previous_hash": row.get("previous_hash"),
        }
        for row in rows
    ]
    ctx.send_json(200, ctx.paginate(items, total=total, limit=limit, offset=offset))
    return True


def _artifacts_get(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    try:
        data = ctx.runtime.provider.read_artifact(params["hash"])
        ctx.send_json(200, data)
    except FileNotFoundError:
        ctx.not_found()
    except ValueError as exc:
        ctx.send_error(500, "integrity_failed", str(exc))
    return True


def _artifacts_summary(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    try:
        data = ctx.runtime.provider.read_artifact(params["hash"])
        artifact = data.get("artifact", data)
        proposed = artifact.get("proposed_artifact", {})
        output = proposed.get("output", {})
        ctx.send_json(
            200,
            {
                "artifact_hash": data.get("artifact_hash") or params["hash"],
                "attestation_id": artifact.get("attestation_id"),
                "final_status": artifact.get("final_status"),
                "total_redactions": output.get("total_redactions"),
                "governance_decision": artifact.get("governance_decision", {}).get("decision"),
                "compliance_policy_id": artifact.get("compliance_policy_id"),
                "llm_decision": artifact.get("llm_decision"),
                "has_zk": any(k.startswith("zk_proof_") for k in artifact),
            },
        )
    except FileNotFoundError:
        ctx.not_found()
    except ValueError as exc:
        ctx.send_error(500, "integrity_failed", str(exc))
    return True


def _audit_logs(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    ctx.send_json(200, {"logs": ctx.runtime.list_audit_logs()})
    return True


def _audit_entries(ctx: ApiV2Context, query: Dict[str, str], params: Dict[str, str]) -> bool:
    from ..audit_logger import AuditLogger

    log_path = ctx.runtime.base_path / "managed" / "audit" / Path(params["name"]).name
    if not log_path.exists():
        ctx.not_found()
        return True
    limit = ctx.parse_int(query.get("limit"), 50)
    offset = ctx.parse_int(query.get("offset"), 0, maximum=10_000)
    logger = AuditLogger(log_path=log_path)
    entries, total = logger.get_entries_page(offset=offset, limit=limit)
    ctx.send_json(
        200,
        {
            "log": params["name"],
            "chain_valid": logger.verify_chain(),
            **ctx.paginate(entries, total=total, limit=limit, offset=offset),
        },
    )
    return True


def _jobs_list(ctx: ApiV2Context, query: Dict[str, str], _params: Dict[str, str]) -> bool:
    limit = ctx.parse_int(query.get("limit"), 20)
    offset = ctx.parse_int(query.get("offset"), 0, maximum=10_000)
    status = query.get("status")
    jobs = ctx.queue.list_jobs(limit=limit, offset=offset, status=status or None)
    total = ctx.queue.count_jobs(status=status or None)
    ctx.send_json(200, ctx.paginate(jobs, total=total, limit=limit, offset=offset))
    return True


def _jobs_get(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    job = ctx.queue.get(params["id"])
    if not job:
        ctx.not_found()
        return True
    ctx.send_json(200, job)
    return True


def _jobs_stream(ctx: ApiV2Context, query: Dict[str, str], _params: Dict[str, str]) -> bool:
    handler = ctx.handler
    ctx.begin_event_stream()

    duration = ctx.parse_int(query.get("seconds"), 30, minimum=5, maximum=120)
    poll_ms = ctx.parse_int(query.get("poll_ms"), 1000, minimum=250, maximum=5000)
    deadline = time.time() + duration
    seen: Dict[str, str] = {}

    while time.time() < deadline:
        jobs = ctx.queue.list_jobs(limit=50, offset=0)
        for job in jobs:
            job_id = job["id"]
            status = job["status"]
            if seen.get(job_id) == status:
                continue
            seen[job_id] = status
            payload = json.dumps({"job_id": job_id, "status": status, "job": job}, default=str)
            handler.wfile.write(f"event: job\ndata: {payload}\n\n".encode("utf-8"))
            handler.wfile.flush()
        time.sleep(poll_ms / 1000.0)

    handler.wfile.write(b"event: close\ndata: {}\n\n")
    handler.wfile.flush()
    return True


def _pipeline_run(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    body = ctx.read_json()
    payload = {
        "pack": body.get("pack", "reference"),
        "input_text": body.get("input_text"),
        "upload_id": (body.get("input_files") or [None])[0] if body.get("input_files") else body.get("upload_id"),
        "attest": bool(body.get("attest", False)),
        "llm": body.get("llm"),
        "proof_profile": body.get("proof_profile") or body.get("proof_profile_id"),
    }
    if body.get("input_files"):
        payload["upload_id"] = body["input_files"][0]
    if body.get("pipeline_id") or body.get("pipeline"):
        payload["pipeline_id"] = body.get("pipeline_id") or body.get("pipeline")
    if body.get("pipeline_document"):
        payload["pipeline_document"] = body["pipeline_document"]

    run_async = body.get("async", True)
    if run_async:
        job = ctx.queue.enqueue("pipeline", payload)
        ctx.send_json(202, {"message": "job queued", **job})
        return True

    try:
        result = execute_job_payload(payload, runtime=ctx.runtime)
        ctx.send_json(200, {"message": "pipeline complete", "result": result})
    except Exception as exc:
        ctx.send_error(500, "pipeline_failed", str(exc))
    return True


def _pipelines_list(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    from ..pipeline_store import list_pipelines

    ctx.send_json(200, {"pipelines": list_pipelines(ctx.runtime.base_path)})
    return True


def _examples_pipelines_dir(base_path: Path) -> Path:
    from ..pack_catalog import resolve_apxv_root

    root = resolve_apxv_root(base_path)
    return root / "examples" / "pipelines"


def _pipelines_templates_list(
    ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]
) -> bool:
    from ..pipeline_spec import load_pipeline_file, validate_pipeline_document

    directory = _examples_pipelines_dir(ctx.runtime.base_path)
    templates: List[Dict[str, Any]] = []
    if directory.is_dir():
        for path in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")) + sorted(
            directory.glob("*.json")
        ):
            try:
                raw = load_pipeline_file(path)
                result = validate_pipeline_document(raw)
                if not result.ok or result.document is None:
                    continue
                doc = result.document
                templates.append(
                    {
                        "id": doc["id"],
                        "name": doc.get("name"),
                        "version": doc.get("version"),
                        "description": doc.get("description"),
                        "step_count": len(doc.get("steps", [])),
                        "maturity": "Example",
                        "path": str(path.name),
                    }
                )
            except Exception:
                continue
    ctx.send_json(200, {"templates": templates})
    return True


def _pipelines_templates_get(
    ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]
) -> bool:
    from ..pipeline_spec import load_pipeline_file, validate_pipeline_document

    directory = _examples_pipelines_dir(ctx.runtime.base_path)
    template_id = params["id"]
    candidates = [
        directory / f"{template_id}.yaml",
        directory / f"{template_id}.yml",
        directory / f"{template_id}.json",
    ]
    path = next((p for p in candidates if p.is_file()), None)
    if path is None and directory.is_dir():
        for p in directory.iterdir():
            if p.suffix.lower() in (".yaml", ".yml", ".json"):
                try:
                    raw = load_pipeline_file(p)
                    if isinstance(raw, dict) and raw.get("id") == template_id:
                        path = p
                        break
                except Exception:
                    continue
    if path is None or not path.is_file():
        ctx.send_error(404, "template_not_found", f"template not found: {template_id}")
        return True
    content = path.read_text(encoding="utf-8")
    try:
        raw = load_pipeline_file(path)
        result = validate_pipeline_document(raw)
        doc = result.document if result.ok else None
    except Exception:
        doc = None
    ctx.send_json(
        200,
        {
            "template": {
                "id": (doc or {}).get("id") or template_id,
                "name": (doc or {}).get("name"),
                "version": (doc or {}).get("version"),
                "description": (doc or {}).get("description"),
                "step_count": len((doc or {}).get("steps") or []),
                "maturity": "Example",
                "path": path.name,
            },
            "content": content,
            "pipeline": doc,
        },
    )
    return True


def _pipelines_get(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    from ..pipeline_store import PipelineStoreError, load_pipeline

    try:
        doc = load_pipeline(ctx.runtime.base_path, params["id"])
        ctx.send_json(200, {"pipeline": doc})
    except PipelineStoreError as exc:
        ctx.send_error(404, "pipeline_not_found", str(exc))
    except Exception as exc:
        ctx.send_error(400, "pipeline_invalid", str(exc))
    return True


def _pipelines_create(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    from ..pipeline_spec import PipelineSpecError, validate_pipeline_document
    from ..pipeline_store import PipelineStoreError, save_pipeline

    body = ctx.read_json()
    document = body.get("pipeline") or body.get("document") or body
    if "pipeline" in body or "document" in body:
        document = body.get("pipeline") or body.get("document")
    try:
        result = validate_pipeline_document(document)
        doc = result.raise_if_invalid()
        path = save_pipeline(
            ctx.runtime.base_path,
            doc,
            fmt=str(body.get("format") or "yaml"),
            overwrite=bool(body.get("overwrite", True)),
        )
        ctx.send_json(
            201,
            {
                "message": "pipeline saved",
                "pipeline": doc,
                "path": str(path),
                "warnings": result.warnings,
            },
        )
    except (PipelineSpecError, PipelineStoreError) as exc:
        ctx.send_error(400, "pipeline_invalid", str(exc))
    except Exception as exc:
        ctx.send_error(500, "pipeline_save_failed", str(exc))
    return True


def _pipelines_validate(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    from ..pipeline_spec import validate_pipeline_document

    body = ctx.read_json()
    document = body.get("pipeline") or body.get("document") or body
    result = validate_pipeline_document(document)
    ctx.send_json(
        200 if result.ok else 400,
        {
            "ok": result.ok,
            "errors": result.errors,
            "warnings": result.warnings,
            "pipeline": result.document,
        },
    )
    return True


def _pipelines_import(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    from ..pipeline_store import PipelineStoreError, import_pipeline_text
    from ..pipeline_spec import PipelineSpecError

    body = ctx.read_json()
    text = body.get("content") or body.get("text")
    if not text:
        ctx.send_error(400, "missing_content", "content is required")
        return True
    try:
        imported = import_pipeline_text(
            ctx.runtime.base_path,
            text,
            fmt=str(body.get("format") or "auto"),
            overwrite=bool(body.get("overwrite", True)),
        )
        ctx.send_json(201, {"message": "pipeline imported", **imported})
    except (PipelineSpecError, PipelineStoreError) as exc:
        ctx.send_error(400, "pipeline_import_failed", str(exc))
    return True


def _pipelines_export(ctx: ApiV2Context, query: Dict[str, str], params: Dict[str, str]) -> bool:
    from ..pipeline_store import PipelineStoreError, export_pipeline

    fmt = query.get("format") or "yaml"
    try:
        content = export_pipeline(ctx.runtime.base_path, params["id"], fmt=fmt)
        ctx.send_json(
            200,
            {"pipeline_id": params["id"], "format": fmt, "content": content},
        )
    except PipelineStoreError as exc:
        ctx.send_error(404, "pipeline_not_found", str(exc))
    except Exception as exc:
        ctx.send_error(400, "pipeline_export_failed", str(exc))
    return True


def _pipelines_run(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    try:
        body = ctx.read_json()
        if not isinstance(body, dict):
            body = {}
    except Exception:
        body = {}
    payload = {
        "pipeline_id": params["id"],
        "input_text": body.get("input_text"),
        "upload_id": body.get("upload_id"),
        "attest": body.get("attest"),
        "llm": body.get("llm"),
        "proof_profile": body.get("proof_profile") or body.get("proof_profile_id"),
    }
    run_async = body.get("async", True)
    if run_async:
        job = ctx.queue.enqueue("pipeline", payload)
        ctx.send_json(202, {"message": "job queued", **job})
        return True
    try:
        result = execute_job_payload(payload, runtime=ctx.runtime)
        ctx.send_json(200, {"message": "pipeline complete", "result": result})
    except Exception as exc:
        ctx.send_error(500, "pipeline_failed", str(exc))
    return True


def _pipelines_delete(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    from ..pipeline_store import delete_pipeline

    deleted = delete_pipeline(ctx.runtime.base_path, params["id"])
    if not deleted:
        ctx.send_error(404, "pipeline_not_found", f"pipeline not found: {params['id']}")
        return True
    ctx.send_json(200, {"message": "pipeline deleted", "id": params["id"]})
    return True


def _jobs_approve(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    body = {}
    try:
        body = ctx.read_json()
        if not isinstance(body, dict):
            body = {}
    except Exception:
        body = {}
    job = ctx.queue.get(params["id"])
    if not job:
        ctx.send_error(404, "job_not_found", f"job not found: {params['id']}")
        return True
    if job.get("status") != "awaiting_approval":
        ctx.send_error(
            400,
            "job_not_awaiting_approval",
            f"job status is {job.get('status')!r}, expected awaiting_approval",
        )
        return True
    result = job.get("result") or {}
    pause = result.get("pause") or {}
    resume_state = pause.get("resume_state")
    if not resume_state:
        ctx.send_error(400, "missing_resume_state", "job has no pause.resume_state")
        return True
    approved = body.get("approved", True)
    if approved is False or str(approved).lower() in ("0", "false", "no"):
        payload = {
            "resume_approval": True,
            "resume_state": resume_state,
            "approved": False,
            "note": body.get("note") or "operator rejected",
        }
    else:
        payload = {
            "resume_approval": True,
            "resume_state": resume_state,
            "approved": True,
            "note": body.get("note") or "",
        }
    requeued = ctx.queue.resume_from_approval(params["id"], payload)
    if not requeued:
        ctx.send_error(500, "resume_failed", "could not re-queue job")
        return True
    run_async = body.get("async", True)
    if run_async:
        ctx.send_json(202, {"message": "approval accepted; job re-queued", **requeued})
        return True
    try:
        result = execute_job_payload(payload, runtime=ctx.runtime)
        if (
            isinstance(result, dict)
            and result.get("final_status") == "awaiting_approval"
        ):
            ctx.queue.pause_awaiting_approval(params["id"], result)
        else:
            ctx.queue.complete(params["id"], result)
        ctx.send_json(200, {"message": "pipeline continued", "result": result})
    except Exception as exc:
        ctx.queue.fail(params["id"], str(exc), retry=False)
        ctx.send_error(500, "pipeline_failed", str(exc))
    return True


def _catalog_lint(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    from ..catalog_quality import lint_catalog

    ctx.send_json(200, lint_catalog(ctx.runtime.base_path))
    return True


def _catalog_smoke(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    from ..catalog_quality import smoke_pipeline

    body = ctx.read_json()
    pipeline_id = str(body.get("pipeline_id") or "").strip()
    if not pipeline_id:
        ctx.send_error(400, "missing_pipeline_id", "pipeline_id is required")
        return True
    report = smoke_pipeline(ctx.runtime.base_path, pipeline_id)
    ctx.send_json(200 if report.get("ok") else 400, report)
    return True


def _swarms_list(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    from ..swarm import list_swarms

    ctx.send_json(200, {"swarms": list_swarms(ctx.runtime.base_path)})
    return True


def _swarms_run(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    from ..swarm import run_swarm

    body = ctx.read_json()
    pipeline_ids = body.get("pipeline_ids") or []
    if not isinstance(pipeline_ids, list) or not pipeline_ids:
        ctx.send_error(400, "missing_pipeline_ids", "pipeline_ids array is required")
        return True
    try:
        record = run_swarm(
            runtime=ctx.runtime,
            name=str(body.get("name") or "swarm"),
            pipeline_ids=[str(p) for p in pipeline_ids],
            input_text=body.get("input_text"),
            attest_each=bool(body.get("attest_each", False)),
        )
        ctx.send_json(200, {"message": "swarm complete", "swarm": record})
    except Exception as exc:
        ctx.send_error(500, "swarm_failed", str(exc))
    return True


def _swarms_get(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    from ..swarm import get_swarm

    record = get_swarm(ctx.runtime.base_path, params["id"])
    if not record:
        ctx.send_error(404, "swarm_not_found", f"swarm not found: {params['id']}")
        return True
    ctx.send_json(200, {"swarm": record})
    return True


def _packs_list(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    ctx.send_json(200, {"packs": list_packs(ctx.runtime.base_path)})
    return True


def _packs_create(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    body = ctx.read_json()
    pack_id = str(body.get("pack_id") or body.get("id") or "").strip()
    name = str(body.get("name") or pack_id).strip()
    if not pack_id:
        ctx.send_error(400, "missing_pack_id", "pack_id is required")
        return True
    try:
        result = create_pack(
            ctx.runtime.base_path,
            pack_id=pack_id,
            name=name,
            description=str(body.get("description") or ""),
            template=str(body.get("template") or "reference"),
        )
        ctx.send_json(201, {"message": "pack created", "pack": result})
    except (ValueError, FileNotFoundError) as exc:
        ctx.send_error(400, "pack_create_failed", str(exc))
    return True


def _packs_get(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    pack = get_pack(ctx.runtime.base_path, params["id"])
    if not pack:
        ctx.not_found()
        return True
    ctx.send_json(200, pack)
    return True


def _packs_agents(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    if not get_pack(ctx.runtime.base_path, params["id"]):
        ctx.not_found()
        return True
    result = agents_for_pack(ctx.runtime.base_path, params["id"], runtime=ctx.runtime)
    ctx.send_json(200, result)
    return True


def _agents_list(ctx: ApiV2Context, query: Dict[str, str], _params: Dict[str, str]) -> bool:
    limit = ctx.parse_int(query.get("limit"), 100)
    offset = ctx.parse_int(query.get("offset"), 0, maximum=10_000)
    agents = list_agents(ctx.runtime.base_path, runtime=ctx.runtime)
    page = agents[offset : offset + limit]
    ctx.send_json(200, ctx.paginate(page, total=len(agents), limit=limit, offset=offset))
    return True


def _agents_get(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    agent = get_agent(ctx.runtime.base_path, params["id"], runtime=ctx.runtime)
    if not agent:
        ctx.not_found()
        return True
    ctx.send_json(200, agent)
    return True


def _studio_agents_list(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    ctx.send_json(200, {"agents": list_operator_agents(ctx.runtime.base_path)})
    return True


def _studio_agents_save(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    body = ctx.read_json()
    try:
        agent = save_operator_agent(
            ctx.runtime,
            agent_id=str(body.get("id") or body.get("agent_id") or ""),
            name=str(body.get("name") or ""),
            description=str(body.get("description") or ""),
            agent_type=str(body.get("agent_type") or "agentic"),
            instruction_md=str(body.get("instruction_md") or body.get("instruction") or ""),
            knowledge_md=str(body.get("knowledge_md") or body.get("knowledge") or ""),
            capabilities=body.get("capabilities"),
        )
    except StudioError as exc:
        ctx.send_json(400, {"error": "studio_error", "message": str(exc)})
        return True
    ctx.send_json(200, {"message": "Agent saved and registered", "agent": agent})
    return True


def _studio_agents_get(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    agent = load_operator_agent(ctx.runtime.base_path, params["id"])
    if not agent:
        ctx.not_found()
        return True
    ctx.send_json(200, agent)
    return True


def _studio_agents_test(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    try:
        body = ctx.read_json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    try:
        result = run_operator_agent_test(
            ctx.runtime,
            params["id"],
            input_text=str(
                body.get("input_text")
                or "Studio test sample: contact test@example.com"
            ),
        )
    except StudioError as exc:
        ctx.send_json(400, {"error": "studio_error", "message": str(exc)})
        return True
    except Exception as exc:
        ctx.send_json(500, {"error": "test_failed", "message": str(exc)})
        return True
    ctx.send_json(200, result)
    return True


def _studio_agents_promote(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    body = {}
    try:
        body = ctx.read_json()
    except Exception:
        body = {}
    try:
        agent = promote_agent(
            ctx.runtime,
            params["id"],
            force=bool((body or {}).get("force")),
        )
    except StudioError as exc:
        ctx.send_json(400, {"error": "studio_error", "message": str(exc)})
        return True
    ctx.send_json(200, {"message": "Agent promoted to Workbench shelf", "agent": agent})
    return True


def _studio_packs_list(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    ctx.send_json(200, {"packs": list_studio_packs(ctx.runtime.base_path)})
    return True


def _studio_packs_save(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    body = ctx.read_json()
    try:
        pack = save_studio_pack(
            ctx.runtime,
            pack_id=str(body.get("id") or body.get("pack_id") or ""),
            name=str(body.get("name") or ""),
            description=str(body.get("description") or ""),
            rules_md=str(body.get("rules_md") or body.get("rules") or ""),
            workflow_md=str(body.get("workflow_md") or body.get("workflow") or ""),
            knowledge_md=str(body.get("knowledge_md") or body.get("knowledge") or ""),
            agent_ids=body.get("agent_ids") or body.get("agents"),
        )
    except StudioError as exc:
        ctx.send_json(400, {"error": "studio_error", "message": str(exc)})
        return True
    ctx.send_json(200, {"message": "Pack saved", "pack": pack})
    return True


def _studio_packs_get(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    try:
        pack = get_studio_pack(ctx.runtime.base_path, params["id"])
    except StudioError:
        ctx.not_found()
        return True
    ctx.send_json(200, pack)
    return True


def _studio_packs_test(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    body = {}
    try:
        body = ctx.read_json()
    except Exception:
        body = {}
    try:
        result = run_studio_pack_test(
            ctx.runtime,
            params["id"],
            input_text=str(
                (body or {}).get("input_text")
                or "Studio pack test: email demo@example.com"
            ),
        )
    except StudioError as exc:
        ctx.send_json(400, {"error": "studio_error", "message": str(exc)})
        return True
    except Exception as exc:
        ctx.send_json(500, {"error": "test_failed", "message": str(exc)})
        return True
    ctx.send_json(200, result)
    return True


def _studio_packs_promote(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    body = {}
    try:
        body = ctx.read_json()
    except Exception:
        body = {}
    try:
        pack = promote_pack(
            ctx.runtime,
            params["id"],
            force=bool((body or {}).get("force")),
        )
    except StudioError as exc:
        ctx.send_json(400, {"error": "studio_error", "message": str(exc)})
        return True
    ctx.send_json(200, {"message": "Pack promoted to Workbench shelf", "pack": pack})
    return True


def _studio_shelf(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    ctx.send_json(200, list_promoted_for_workbench(ctx.runtime.base_path))
    return True


def _studio_proofs_list(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    ctx.send_json(200, {"proofs": list_proof_profiles(ctx.runtime.base_path)})
    return True


def _studio_proofs_catalog(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    ctx.send_json(200, {"predicates": list_predicate_catalog()})
    return True


def _studio_proofs_templates(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    ctx.send_json(200, {"templates": list_proof_templates()})
    return True


def _studio_proofs_from_template(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    try:
        body = ctx.read_json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    try:
        proof = save_from_template(
            ctx.runtime,
            str(body.get("template_id") or body.get("id") or ""),
            proof_id=body.get("proof_id") or body.get("new_id"),
            name=body.get("name"),
        )
    except StudioError as exc:
        ctx.send_json(400, {"error": "studio_error", "message": str(exc)})
        return True
    ctx.send_json(200, {"message": "Proof profile created from template", "proof": proof})
    return True


def _studio_proofs_status(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    ctx.send_json(
        200,
        {
            "universal_predicate_v1": {
                "keys_available": universal_keys_available(ctx.runtime.base_path),
                "circuit": "universal-predicate-v1",
            },
            "predicate_count": len(list_predicate_catalog()),
            "template_count": len(list_proof_templates()),
        },
    )
    return True


def _studio_proofs_compile_intent(
    ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]
) -> bool:
    try:
        body = ctx.read_json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    intent = str(body.get("intent_md") or body.get("intent") or body.get("text") or "")
    try:
        compiled = compile_intent(
            intent,
            proof_id=str(body.get("proof_id") or body.get("id") or "APXV-PROOF-FROM-INTENT"),
            name=str(body.get("name") or "From intent"),
            use_llm=bool(body.get("use_llm")),
        )
    except StudioError as exc:
        ctx.send_json(400, {"error": "studio_error", "message": str(exc)})
        return True
    except Exception as exc:
        ctx.send_json(400, {"error": "compile_failed", "message": str(exc)})
        return True
    ctx.send_json(200, compiled)
    return True


def _studio_proofs_from_intent(
    ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]
) -> bool:
    try:
        body = ctx.read_json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    try:
        proof = save_profile_from_intent(
            ctx.runtime,
            intent_md=str(body.get("intent_md") or body.get("intent") or ""),
            proof_id=str(body.get("proof_id") or body.get("id") or "APXV-PROOF-FROM-INTENT"),
            name=str(body.get("name") or "From intent"),
            prefer_universal=bool(body.get("prefer_universal", True)),
        )
    except StudioError as exc:
        ctx.send_json(400, {"error": "studio_error", "message": str(exc)})
        return True
    ctx.send_json(200, {"message": "Proof profile saved from intent", "proof": proof})
    return True


def _studio_proofs_export_claim(
    ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]
) -> bool:
    try:
        body = ctx.read_json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    bundle = export_proof_claim_bundle(
        ctx.runtime.base_path,
        proof_profile_id=body.get("proof_profile_id") or body.get("proof_id"),
        claim=body.get("claim") if isinstance(body.get("claim"), dict) else None,
        attested=body.get("attested") if isinstance(body.get("attested"), dict) else None,
    )
    ctx.send_json(200, {"bundle": bundle})
    return True


def _studio_proofs_save(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    body = ctx.read_json()
    try:
        proof = save_proof_profile(
            ctx.runtime,
            proof_id=str(body.get("id") or body.get("proof_id") or ""),
            name=str(body.get("name") or ""),
            description=str(body.get("description") or ""),
            intent_md=str(body.get("intent_md") or body.get("intent") or ""),
            predicates=body.get("predicates"),
            circuit_binding=str(
                body.get("circuit_binding") or "existing-dual-track"
            ),
            fail_closed=bool(body.get("fail_closed", True)),
            require_attest=body.get("require_attest"),
        )
    except StudioError as exc:
        ctx.send_json(400, {"error": "studio_error", "message": str(exc)})
        return True
    ctx.send_json(200, {"message": "Proof profile saved", "proof": proof})
    return True


def _studio_proofs_get(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    try:
        proof = get_proof_profile(ctx.runtime.base_path, params["id"])
    except StudioError:
        ctx.not_found()
        return True
    ctx.send_json(200, proof)
    return True


def _studio_proofs_test(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    body: Dict[str, Any] = {}
    try:
        body = ctx.read_json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    try:
        result = run_proof_profile_test(
            ctx.runtime,
            params["id"],
            input_text=body.get("input_text"),
        )
    except StudioError as exc:
        ctx.send_json(400, {"error": "studio_error", "message": str(exc)})
        return True
    except Exception as exc:
        ctx.send_json(500, {"error": "test_failed", "message": str(exc)})
        return True
    ctx.send_json(200, result)
    return True


def _studio_proofs_promote(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    body: Dict[str, Any] = {}
    try:
        body = ctx.read_json()
    except Exception:
        body = {}
    try:
        proof = promote_proof_profile(
            ctx.runtime,
            params["id"],
            force=bool((body or {}).get("force")),
        )
    except StudioError as exc:
        ctx.send_json(400, {"error": "studio_error", "message": str(exc)})
        return True
    ctx.send_json(
        200,
        {"message": "Proof profile promoted to Workbench shelf", "proof": proof},
    )
    return True


def _packs_active(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    ctx.send_json(200, get_active_pack_summary(ctx.runtime.base_path))
    return True


def _packs_activate(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    body = ctx.read_json()
    confirm = bool(body.get("confirm"))
    activated_by = str(body.get("activated_by") or "operator")
    try:
        result = activate_pack(
            ctx.runtime,
            params["id"],
            confirm=confirm,
            activated_by=activated_by,
        )
        ctx.send_json(200, {"message": "pack activated", **result})
    except PackInstallError as exc:
        ctx.send_error(400, "pack_activate_failed", str(exc))
    return True


def _packs_clone(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    body = ctx.read_json()
    new_pack_id = str(body.get("pack_id") or body.get("id") or "").strip()
    name = str(body.get("name") or new_pack_id).strip()
    if not new_pack_id:
        ctx.send_error(400, "missing_pack_id", "pack_id is required for clone target")
        return True
    try:
        result = clone_pack(
            ctx.runtime.base_path,
            params["id"],
            new_pack_id=new_pack_id,
            name=name,
            description=str(body.get("description") or ""),
        )
        ctx.send_json(201, {"message": "pack cloned", "pack": result})
    except PackInstallError as exc:
        ctx.send_error(400, "pack_clone_failed", str(exc))
    return True


def _governance_specs(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    specs: Dict[str, Any] = {}
    for spec_type in ("rule", "workflow", "knowledge"):
        try:
            specs[spec_type] = ctx.runtime.provider.read_specification(spec_type)
        except FileNotFoundError:
            specs[spec_type] = None
    ctx.send_json(200, {"specs": specs, "status": ctx.runtime.governance.get_status()})
    return True


def _governance_proposals_list(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    proposals = ctx.runtime.governance.list_proposals(limit=50)
    ctx.send_json(200, {"proposals": proposals})
    return True


def _governance_proposals_get(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    proposal = ctx.runtime.governance.get_proposal(params["proposal_id"])
    if not proposal:
        ctx.not_found()
        return True
    content = ""
    relpath = proposal.get("proposed_content_relpath")
    if relpath:
        proposal_path = ctx.runtime.base_path / "managed" / relpath
        if proposal_path.exists():
            content = proposal_path.read_text(encoding="utf-8")
    ctx.send_json(200, {"proposal": proposal, "content": content})
    return True


def _governance_proposals_create(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    body = ctx.read_json()
    try:
        result = ctx.runtime.governance.propose_change(
            spec_type=body.get("spec_type", ""),
            content=body.get("content", ""),
            proposed_by=body.get("proposed_by", "api-operator"),
            summary=body.get("summary", ""),
        )
        ctx.send_json(201, {"message": "proposal created", "proposal": result})
    except (GovernanceApprovalError, ValueError) as exc:
        ctx.send_error(400, "proposal_failed", str(exc))
    return True


def _governance_proposals_action(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    body = ctx.read_json()
    governance = ctx.runtime.governance
    proposal_id = params["proposal_id"]
    action = params["action"]
    try:
        if action == "approve":
            result = governance.approve_proposal(
                proposal_id,
                approved_by=body.get("approved_by", "api-operator"),
            )
            ctx.send_json(200, {"message": "proposal approved", **result})
            return True
        if action == "reject":
            result = governance.reject_proposal(
                proposal_id,
                rejected_by=body.get("rejected_by", "api-operator"),
                reason=body.get("reason", ""),
            )
            ctx.send_json(200, {"message": "proposal rejected", "proposal": result})
            return True
        if action == "apply":
            result = governance.apply_proposal(proposal_id)
            ctx.send_json(200, {"message": "proposal applied", "proposal": result})
            return True
    except GovernanceApprovalError as exc:
        ctx.send_error(400, "governance_action_failed", str(exc))
    return True


def _capabilities_get(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    ctx.send_json(200, ctx.runtime.capability_checker.get_status())
    return True


def _backups_list(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    backups = ctx.runtime.backup_manager.list_backups()
    ctx.send_json(200, {"backups": backups})
    return True


def _backups_create(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    try:
        result = ctx.runtime.backup_manager.create_backup()
        ctx.send_json(201, {"message": "backup created", **result})
    except BackupRestoreError as exc:
        ctx.send_error(500, "backup_failed", str(exc))
    return True


def _backups_restore(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    body = ctx.read_json()
    archive_name = body.get("filename") or body.get("archive")
    if not archive_name:
        ctx.send_error(400, "missing_filename", "filename or archive required")
        return True
    archive_path = ctx.runtime.backup_manager.backup_dir / Path(archive_name).name
    try:
        result = ctx.runtime.backup_manager.restore_backup(
            archive_path,
            dry_run=bool(body.get("dry_run", False)),
            create_safety_backup=not bool(body.get("no_safety_backup", False)),
        )
        ctx.send_json(200, {"message": "backup restored", **result})
    except BackupRestoreError as exc:
        ctx.send_error(400, "restore_failed", str(exc))
    return True


def _keys_list(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    ctx.auth.reload()
    ctx.send_json(200, {"keys": ctx.auth.list_keys()})
    return True


def _keys_create(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    body = ctx.read_json()
    key_id = body.get("id")
    if not key_id:
        ctx.send_error(400, "missing_id", "id is required")
        return True
    try:
        raw = ctx.auth.create_key(
            key_id,
            description=body.get("description", ""),
            role=body.get("role", "operator"),
        )
        ctx.send_json(
            201,
            {
                "id": key_id,
                "api_key": raw,
                "message": "Save this key now — it cannot be retrieved later.",
            },
        )
    except ValueError as exc:
        ctx.send_error(400, "key_create_failed", str(exc))
    return True


def _keys_delete(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    try:
        ctx.auth.revoke_key(params["id"])
        ctx.send_json(200, {"message": "key revoked", "id": params["id"]})
    except ValueError as exc:
        ctx.send_error(400, "key_revoke_failed", str(exc))
    return True


def _verify_attestation(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    body = ctx.read_json()
    try:
        attested = load_attested_for_verify(
            runtime=ctx.runtime,
            artifact_hash=body.get("artifact_hash"),
            inline=body.get("attestation"),
            base_path=ctx.runtime.base_path,
        )
        report = verify_attestation_artifact(
            attested,
            base_path=ctx.runtime.base_path,
            real_zk=bool(body.get("real_zk", False)),
        )
        ctx.send_json(200, report)
    except (ValueError, FileNotFoundError) as exc:
        ctx.send_error(400, "verify_failed", str(exc))
    return True


def _integrations_ollama(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    from scripts.bootstrap.install_ollama import get_ollama_api_status

    ctx.send_json(200, get_ollama_api_status(timeout=2.0))
    return True


def _integrations_repair(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    from scripts.bootstrap.integrations import repair_integrations

    result = repair_integrations(ctx.runtime.base_path)
    ctx.send_json(200, result)
    return True


def _uploads_create(ctx: ApiV2Context, _query: Dict[str, str], _params: Dict[str, str]) -> bool:
    content_type = ctx.handler.headers.get("Content-Type", "")
    if "multipart/form-data" not in content_type:
        ctx.send_error(400, "invalid_content_type", "multipart/form-data required")
        return True
    try:
        parsed = parse_multipart_form(ctx.read_raw_body(), content_type)
        session = ctx.uploads.create_session(label=parsed["fields"].get("label", ""))
        if parsed["files"]:
            ctx.uploads.add_files(session["upload_id"], parsed["files"])
            session = ctx.uploads.get_session(session["upload_id"])
        ctx.send_json(201, {"message": "upload session created", "session": session})
    except (ValueError, FileNotFoundError) as exc:
        ctx.send_error(400, "upload_failed", str(exc))
    return True


def _uploads_get(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    session = ctx.uploads.get_session(params["id"])
    if not session:
        ctx.not_found()
        return True
    ctx.send_json(200, session)
    return True


def _uploads_delete(ctx: ApiV2Context, _query: Dict[str, str], params: Dict[str, str]) -> bool:
    if not ctx.uploads.delete_session(params["id"]):
        ctx.not_found()
        return True
    ctx.send_json(200, {"message": "upload session deleted", "upload_id": params["id"]})
    return True