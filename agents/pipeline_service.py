"""
APXV — Pipeline Service (quiet execution for local API)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import importlib.util
import sys

from .pack_catalog import find_pack, resolve_apxv_root, resolve_pack_key
from .runtime import APXRuntime


def _load_module_from_file(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _pack_module(base_path: Path, pack_key: str):
    apx_root = resolve_apxv_root(base_path)
    files = {
        "document": apx_root
        / "governance-libraries"
        / "apxv-pack-document-processing"
        / "agents"
        / "document_agents.py",
        "ai": apx_root
        / "governance-libraries"
        / "apxv-pack-ai-governance"
        / "agents"
        / "governance_agents.py",
    }
    path = files[pack_key]
    return _load_module_from_file(f"apxv_pack_{pack_key}", path)


def _load_pack_agents_module(base_path: Path, pack_dir: Path, pack_id: str):
    agents_dir = pack_dir / "agents"
    candidates = [
        agents_dir / "custom_agents.py",
        agents_dir / "reference_agents.py",
        agents_dir / "document_agents.py",
        agents_dir / "governance_agents.py",
    ]
    for path in candidates:
        if path.is_file():
            return _load_module_from_file(f"apxv_pack_{pack_id}", path)
    py_files = sorted(agents_dir.glob("*.py"))
    py_files = [p for p in py_files if p.name != "__init__.py"]
    if not py_files:
        raise FileNotFoundError(f"No agent module in {agents_dir}")
    return _load_module_from_file(f"apxv_pack_{pack_id}", py_files[0])


def _run_custom_pack(
    *,
    pack_entry: Dict[str, Any],
    runtime: APXRuntime,
    input_text: Optional[str],
    upload_id: Optional[str],
    llm: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    apx_root = resolve_apxv_root(runtime.base_path)
    pack_dir = apx_root / pack_entry["path"]
    mod = _load_pack_agents_module(runtime.base_path, pack_dir, pack_entry["id"])

    if upload_id and hasattr(mod, "process_batch_directory"):
        from .upload_manager import UploadManager

        batch_dir = UploadManager(runtime.base_path).batch_directory(upload_id)
        return mod.process_batch_directory(batch_dir, runtime=runtime)

    runner = getattr(mod, "run_pack_pipeline", None) or getattr(
        mod, "run_governed_ai_pipeline", None
    )
    if runner is None:
        raise ValueError(
            f"Pack {pack_entry['id']} has no run_pack_pipeline entry point"
        )

    kwargs: Dict[str, Any] = {"runtime": runtime}
    if input_text is not None:
        kwargs["input_text"] = input_text
    if upload_id is not None:
        kwargs["upload_id"] = upload_id
    if getattr(runner, "__name__", "") == "run_governed_ai_pipeline":
        kwargs["backend"] = _resolve_llm_backend(llm, runtime)

    try:
        return runner(**kwargs)
    except TypeError:
        return runner(input_text or getattr(mod, "SAMPLE_INPUT", ""), runtime=runtime)


def run_pack_pipeline(
    *,
    pack: str = "reference",
    input_text: Optional[str] = None,
    upload_id: Optional[str] = None,
    runtime: Optional[APXRuntime] = None,
    llm: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Dispatch to official pack runners and return attested_result."""
    runtime = runtime or APXRuntime()
    pack_entry = find_pack(runtime.base_path, pack)
    key = resolve_pack_key(pack, runtime.base_path)

    if key == "reference":
        from agents.agent1 import RuleGovernedRedactor
        from agents.agent2 import WorkflowOrchestrator
        from agents.agent3 import AttestationCoordinator

        if input_text is None:
            input_text = (
                "Contact John at john.doe@example.com or call (555) 123-4567. "
                "SSN: 123-45-6789. Card: 4111 1111 1111 1111."
            )
        redactor = RuleGovernedRedactor(runtime=runtime)
        redactor_output = redactor.process_text(input_text)
        orchestrator = WorkflowOrchestrator(runtime=runtime)
        workflow_output = orchestrator.execute_workflow(redactor_output=redactor_output)
        coordinator = AttestationCoordinator(runtime=runtime)
        return coordinator.coordinate_attestation(workflow_output=workflow_output)["attested_result"]

    if key == "document":
        mod = _pack_module(runtime.base_path, "document")
        if not upload_id:
            raise ValueError("document pack requires upload_id")
        from .upload_manager import UploadManager

        batch_dir = UploadManager(runtime.base_path).batch_directory(upload_id)
        return mod.process_batch_directory(batch_dir, runtime=runtime)

    if key == "ai":
        mod = _pack_module(runtime.base_path, "ai")
        return mod.run_governed_ai_pipeline(
            input_text or mod.SAMPLE_INPUT,
            runtime=runtime,
            backend=_resolve_llm_backend(llm, runtime),
        )

    if pack_entry and key == pack_entry["id"]:
        return _run_custom_pack(
            pack_entry=pack_entry,
            runtime=runtime,
            input_text=input_text,
            upload_id=upload_id,
            llm=llm,
        )

    raise ValueError(f"Unsupported pack: {pack}")


def _resolve_llm_backend(llm: Optional[Dict[str, Any]], runtime: APXRuntime):
    from agents.install_profile import resolve_llm_backend

    return resolve_llm_backend(llm, runtime.base_path)


def apply_zk_attestation(attested: Dict[str, Any], runtime: APXRuntime) -> Dict[str, Any]:
    """Attach full governance + entity Groth16 proofs (same path as run_apxv --attest)."""
    from scripts.run_apxv import generate_zk_proof
    from scripts.setup_zk import ensure_zk_setup
    from agents.zk.bridge import generate_entity_proofs
    from agents.zk.bundle import build_dual_proof_bundle, build_governance_proof_bundle

    base = runtime.base_path
    ensure_zk_setup(base_path=base)

    zk_redaction = generate_zk_proof(attested, base, circuit="redaction")
    attested["zk_proof_redaction"] = zk_redaction
    zk_rule = generate_zk_proof(attested, base, circuit="rule-binding", redaction_proof=zk_redaction)
    attested["zk_proof_rule_binding"] = zk_rule
    zk_pipeline = generate_zk_proof(attested, base, circuit="pipeline", redaction_proof=zk_redaction)
    attested["zk_proof_pipeline"] = zk_pipeline

    entity_bundle = generate_entity_proofs(attested, base_path=base)
    attested["entity_proofs"] = entity_bundle
    attested["governance_proofs"] = build_governance_proof_bundle(attested)
    attested["dual_proof_bundle"] = build_dual_proof_bundle(attested)

    zk_summary = {
        "governance": {
            "redaction": zk_redaction.get("verification_result"),
            "rule_binding": zk_rule.get("verification_result"),
            "pipeline": zk_pipeline.get("verification_result"),
        },
        "entity": {
            key: proof.get("verification_result")
            for key, proof in entity_bundle.get("proofs", {}).items()
            if isinstance(proof, dict)
        },
    }
    return zk_summary


def run_pipeline_quiet(
    input_text: Optional[str] = None,
    attest: bool = False,
    runtime: Optional[APXRuntime] = None,
    *,
    pack: str = "reference",
    upload_id: Optional[str] = None,
    llm: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute a governed pack pipeline without CLI output.
    Returns structured result for API/job consumers.
    """
    runtime = runtime or APXRuntime()
    provider = runtime.provider

    attested = run_pack_pipeline(
        pack=pack,
        input_text=input_text,
        upload_id=upload_id,
        runtime=runtime,
        llm=llm,
    )

    artifact_name = "attested_result_pipeline"
    write_meta = provider.write_artifact(artifact=attested, name=artifact_name)

    zk_summary = None
    if attest:
        zk_summary = apply_zk_attestation(attested, runtime)
        write_meta = provider.write_artifact(
            artifact=attested,
            name="attested_result_pipeline_with_zk",
        )
        runtime.system_audit.log_event(
            event_type="pipeline_attested_with_zk",
            data={"attestation_id": attested.get("attestation_id"), "via": "api_v2"},
        )

    runtime.system_audit.log_event(
        event_type="pipeline_completed",
        data={
            "attestation_id": attested.get("attestation_id"),
            "artifact_hash": write_meta["hash"],
            "attest": attest,
            "pack": resolve_pack_key(pack, runtime.base_path),
            "via": "api_v2",
        },
    )

    return {
        "pack": resolve_pack_key(pack, runtime.base_path),
        "attestation_id": attested.get("attestation_id"),
        "final_status": attested.get("final_status"),
        "governance_decision": attested.get("governance_decision", {}).get("decision"),
        "artifact_hash": write_meta["hash"],
        "artifact_path": write_meta["path"],
        "total_redactions": attested.get("proposed_artifact", {})
        .get("output", {})
        .get("total_redactions"),
        "full_provenance_hash": attested.get("full_provenance_hash"),
        "llm_decision": attested.get("llm_decision"),
        "compliance_policy_id": attested.get("compliance_policy_id"),
        "zk_summary": zk_summary,
        "attested_result": attested,
    }


def execute_job_payload(payload: Dict[str, Any], runtime: Optional[APXRuntime] = None) -> Dict[str, Any]:
    return run_pipeline_quiet(
        input_text=payload.get("input_text"),
        attest=bool(payload.get("attest", False)),
        runtime=runtime,
        pack=payload.get("pack", "reference"),
        upload_id=payload.get("upload_id"),
        llm=payload.get("llm"),
    )