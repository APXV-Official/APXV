"""
APXV pipeline runner — ordered/graph steps, pack profiles, HITL, handoff, traces.

Pipeline Spec v0.1+ / product trains v1.5–v1.8.
"""

from __future__ import annotations

import copy
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from .pipeline_profile import pack_profile_context
from .pipeline_service import apply_zk_attestation, run_pack_pipeline
from .pipeline_spec import PipelineSpecError, parse_uses, validate_pipeline_document
from .pipeline_store import PipelineStoreError, load_pipeline
from .runtime import APXRuntime


def _entry_step_ids(doc: Dict[str, Any]) -> List[str]:
    steps = doc.get("steps") or []
    if not steps:
        return []
    edges = doc.get("edges") or []
    if not edges:
        return [steps[0]["id"]]
    incoming = {str(e.get("to")) for e in edges if isinstance(e, dict)}
    roots = [s["id"] for s in steps if s["id"] not in incoming]
    return roots if roots else [steps[0]["id"]]


def _successors(
    doc: Dict[str, Any],
    step_id: str,
    *,
    kinds: Tuple[str, ...],
) -> List[str]:
    """Next step ids via freeform edges, else legacy next_on_* / linear order."""
    edges = doc.get("edges") or []
    if edges:
        out: List[str] = []
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            if edge.get("from") != step_id:
                continue
            kind = edge.get("kind") or "success"
            if kind in kinds:
                target = edge.get("to")
                if isinstance(target, str) and target and target not in out:
                    out.append(target)
        return out

    steps = doc.get("steps") or []
    step_by_id = {s["id"]: (i, s) for i, s in enumerate(steps)}
    if step_id not in step_by_id:
        return []
    index, step = step_by_id[step_id]
    out = []
    if "success" in kinds or "always" in kinds:
        if step.get("next_on_success") and step["next_on_success"] in step_by_id:
            out.append(step["next_on_success"])
        elif index + 1 < len(steps) and "success" in kinds:
            out.append(steps[index + 1]["id"])
    if "failure" in kinds:
        if step.get("next_on_failure") and step["next_on_failure"] in step_by_id:
            out.append(step["next_on_failure"])
    return out


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _summarize_output(output: Any) -> Dict[str, Any]:
    if not isinstance(output, dict):
        return {"type": type(output).__name__}
    summary: Dict[str, Any] = {}
    for key in (
        "agent_id",
        "status",
        "final_status",
        "total_redactions",
        "entity_count",
        "attestation_id",
        "input_hash",
        "approved",
        "handoff_pipeline_id",
        "child_job_hint",
    ):
        if key in output:
            summary[key] = output[key]
    gd = output.get("governance_decision")
    if isinstance(gd, dict) and "decision" in gd:
        summary["governance_decision"] = gd["decision"]
    proposed = output.get("proposed_artifact")
    if isinstance(proposed, dict):
        out = proposed.get("output")
        if isinstance(out, dict) and "total_redactions" in out:
            summary["total_redactions"] = out["total_redactions"]
    return summary


def _require_agent_caps(
    runtime: APXRuntime,
    agent_id: str,
    extra: Optional[List[str]] = None,
) -> None:
    checker = runtime.capability_checker
    required = ["execute_agent"]
    if extra:
        required.extend(extra)
    for cap in required:
        checker.require_capability(agent_id, cap)


def _run_agent_step(
    *,
    agent_id: str,
    runtime: APXRuntime,
    context: Dict[str, Any],
    config: Dict[str, Any],
) -> Any:
    if agent_id == "APXV-AGENT-001":
        from agents.agent1 import RuleGovernedRedactor

        _require_agent_caps(runtime, agent_id, config.get("capabilities_required"))
        agent = RuleGovernedRedactor(runtime=runtime)
        text = context.get("input_text") or ""
        output = agent.process_text(text)
        context["redactor_output"] = output
        context["last_output"] = output
        return output

    if agent_id == "APXV-AGENT-002":
        from agents.agent2 import WorkflowOrchestrator

        _require_agent_caps(runtime, agent_id, config.get("capabilities_required"))
        agent = WorkflowOrchestrator(runtime=runtime)
        redactor_output = context.get("redactor_output")
        if redactor_output is not None:
            output = agent.execute_workflow(redactor_output=redactor_output)
        else:
            output = agent.execute_workflow(input_text=context.get("input_text") or "")
        context["workflow_output"] = output
        context["last_output"] = output
        return output

    if agent_id == "APXV-AGENT-003":
        from agents.agent3 import AttestationCoordinator

        _require_agent_caps(runtime, agent_id, config.get("capabilities_required"))
        agent = AttestationCoordinator(runtime=runtime)
        workflow_output = context.get("workflow_output")
        if workflow_output is None:
            raise PipelineSpecError(
                "APXV-AGENT-003 requires prior workflow_output (run APXV-AGENT-002 first)"
            )
        final = agent.coordinate_attestation(workflow_output=workflow_output)
        attested = final.get("attested_result", final)
        context["attested_result"] = attested
        context["last_output"] = attested
        return attested

    if agent_id == "APXV-AGENT-LLM-001":
        from agents.llm_reasoner import LLMReasoner
        from agents.install_profile import resolve_llm_backend

        _require_agent_caps(runtime, agent_id, config.get("capabilities_required"))
        backend = resolve_llm_backend(context.get("llm"), runtime.base_path)
        reasoner = LLMReasoner(runtime=runtime, backend=backend)
        text = context.get("input_text") or ""
        red = context.get("redactor_output") or {}
        payload = red.get("redacted_text") or text
        agentic = reasoner.execute({"input_text": payload, "text": payload})
        output = agentic.to_dict() if hasattr(agentic, "to_dict") else dict(agentic.__dict__)
        context["llm_output"] = output
        context["last_output"] = output
        return output

    # Studio / operator-defined agents (managed/studio/agents)
    from agents.studio_service import instruction_hash, load_operator_agent

    op_def = load_operator_agent(runtime.base_path, agent_id)
    if op_def:
        _require_agent_caps(runtime, agent_id, config.get("capabilities_required"))
        instruction = op_def.get("instruction_md") or ""
        knowledge = op_def.get("knowledge_md") or ""
        text = context.get("input_text") or ""
        red = context.get("redactor_output") or {}
        if isinstance(red, dict) and red.get("redacted_text"):
            text = red["redacted_text"]
        agent_type = (op_def.get("agent_type") or "agentic").lower()

        if agent_type in ("agentic", "hybrid"):
            from agents.llm_reasoner import LLMReasoner
            from agents.install_profile import resolve_llm_backend

            backend = resolve_llm_backend(context.get("llm"), runtime.base_path)
            reasoner = LLMReasoner(runtime=runtime, backend=backend)
            system = (
                "# Operator agent bound instructions\n\n"
                + instruction
                + "\n\n# Knowledge\n\n"
                + knowledge
            )
            agentic = reasoner.execute(
                {
                    "input_text": text,
                    "text": text,
                    "system": system,
                    "instruction": instruction,
                }
            )
            output = (
                agentic.to_dict() if hasattr(agentic, "to_dict") else dict(agentic.__dict__)
            )
            output["operator_agent_id"] = agent_id
            output["instruction_sha256"] = instruction_hash(instruction)
            context["llm_output"] = output
            context["last_output"] = output
            return output

        # deterministic / tool: bind instruction.md and pass through with proof metadata
        output = {
            "operator_agent_id": agent_id,
            "agent_type": agent_type,
            "instruction_sha256": instruction_hash(instruction),
            "knowledge_sha256": instruction_hash(knowledge),
            "instruction_chars": len(instruction),
            "knowledge_chars": len(knowledge),
            "input_text": text,
            "output_text": text,
            "status": "executed",
            "note": "Operator agent executed under bound instruction.md and knowledge.md",
        }
        context["last_output"] = output
        return output

    raise PipelineSpecError(f"unsupported agent binding in runner: {agent_id}")


def _run_pack_step(
    *,
    pack_id: str,
    runtime: APXRuntime,
    context: Dict[str, Any],
) -> Any:
    attested = run_pack_pipeline(
        pack=pack_id,
        input_text=context.get("input_text"),
        upload_id=context.get("upload_id"),
        runtime=runtime,
        llm=context.get("llm"),
    )
    context["attested_result"] = attested
    context["last_output"] = attested
    return attested


def _run_attest_step(*, runtime: APXRuntime, context: Dict[str, Any]) -> Any:
    attested = context.get("attested_result")
    if not isinstance(attested, dict):
        raise PipelineSpecError("apxv:attest requires attested_result from a prior step")
    zk_summary = apply_zk_attestation(attested, runtime)
    context["zk_summary"] = zk_summary
    context["attest_completed"] = True
    context["last_output"] = {
        "zk_summary": zk_summary,
        "attestation_id": attested.get("attestation_id"),
    }
    return context["last_output"]


def _run_loop_step(*, runtime: APXRuntime, context: Dict[str, Any], config: Dict[str, Any]) -> Any:
    """
    Bounded loop control for Swarm/retry patterns.

    config.max_iterations — hard cap (default 3, max 20)
    Records loop metadata; graph edges still define where to go next.
    """
    try:
        max_iter = int(config.get("max_iterations") or 3)
    except (TypeError, ValueError):
        max_iter = 3
    max_iter = max(1, min(max_iter, 20))
    count = int(context.get("loop_count") or 0) + 1
    context["loop_count"] = count
    context["loop_max"] = max_iter
    if count > max_iter:
        raise PipelineSpecError(
            f"Bounded loop exceeded max_iterations={max_iter}. "
            "Raise the limit on the Loop block or break the cycle."
        )
    output = {
        "loop_count": count,
        "max_iterations": max_iter,
        "status": "continue" if count < max_iter else "last_allowed",
    }
    context["last_output"] = output
    return output


def _run_handoff_step(*, runtime: APXRuntime, context: Dict[str, Any], config: Dict[str, Any]) -> Any:
    """
    Swarm handoff to another composition pipeline.

    config.pipeline_id — required target (another pipeline id on this instance).
    config.run_child — if true (default), run that pipeline now and attach its result.
    """
    target = config.get("pipeline_id") or config.get("target_pipeline_id")
    if not target or not isinstance(target, str) or not str(target).strip():
        raise PipelineSpecError(
            "Handoff has no target pipeline. Select the Handoff block and set "
            "Target pipeline in the inspector (config.pipeline_id), e.g. "
            "apxv-pipeline-reference-linear."
        )
    target = str(target).strip()
    # Prefer redacted text for child when available
    child_input = context.get("input_text")
    red = context.get("redactor_output") or {}
    if isinstance(red, dict) and red.get("redacted_text"):
        child_input = red["redacted_text"]
    ar = context.get("attested_result") or {}
    if isinstance(ar, dict):
        nested = ((ar.get("proposed_artifact") or {}).get("output") or {}).get(
            "redacted_text"
        )
        if nested:
            child_input = nested

    handoff: Dict[str, Any] = {
        "handoff_pipeline_id": target,
        "input_text": child_input,
        "parent_pipeline_id": context.get("pipeline_id"),
        "status": "handoff_recorded",
    }
    # Default: actually run the child composition (swarm v0 behavior operators expect)
    run_child = config.get("run_child")
    if run_child is None:
        run_child = True
    if run_child:
        child_result = run_stored_pipeline(
            target,
            runtime=runtime,
            input_text=child_input,
            upload_id=context.get("upload_id"),
            attest=bool(config.get("child_attest", False)),
            llm=context.get("llm"),
            parent_run={
                "pipeline_id": context.get("pipeline_id"),
                "handoff": True,
            },
            auto_approve=bool(config.get("auto_approve_child", True)),
        )
        handoff["status"] = "child_completed"
        handoff["child_final_status"] = child_result.get("final_status")
        handoff["child_pipeline_id"] = child_result.get("pipeline_id")
        handoff["child_error"] = child_result.get("error")
        if child_result.get("final_status") not in ("succeeded", "awaiting_approval"):
            raise PipelineSpecError(
                f"Handoff child pipeline {target!r} finished with "
                f"{child_result.get('final_status')}: {child_result.get('error') or 'failed'}"
            )
        if child_result.get("attested_result"):
            context["attested_result"] = child_result["attested_result"]
        context["last_output"] = child_result.get("last_output_summary") or handoff
    context.setdefault("handoffs", []).append(handoff)
    context["last_output"] = handoff
    return handoff


def _serializable_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Drop non-JSON-safe values for resume state."""
    keep_keys = (
        "input_text",
        "upload_id",
        "llm",
        "redactor_output",
        "workflow_output",
        "attested_result",
        "llm_output",
        "last_output",
        "zk_summary",
        "attest_completed",
        "handoffs",
        "pipeline_id",
        "artifacts",
        "previous_step_status",
    )
    out: Dict[str, Any] = {}
    for key in keep_keys:
        if key in context:
            try:
                copy.deepcopy(context[key])
                out[key] = context[key]
            except Exception:
                out[key] = _summarize_output(context[key])
    return out


def run_pipeline_document(
    document: Dict[str, Any],
    *,
    runtime: Optional[APXRuntime] = None,
    input_text: Optional[str] = None,
    upload_id: Optional[str] = None,
    attest: Optional[bool] = None,
    llm: Optional[Dict[str, Any]] = None,
    resume_state: Optional[Dict[str, Any]] = None,
    auto_approve: bool = False,
    parent_run: Optional[Dict[str, Any]] = None,
    proof_profile_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a validated pipeline document. Returns job-shaped result with run_trace.

    HITL: uses apxv:approve pauses with final_status=awaiting_approval unless auto_approve.
    proof_profile_id: optional Proof Studio profile (or defaults.proof_profile).
    """
    result = validate_pipeline_document(document)
    doc = result.raise_if_invalid()
    runtime = runtime or APXRuntime()

    defaults = doc.get("defaults") or {}
    default_fail = defaults.get("on_step_failure", "stop")
    want_attest = defaults.get("attest", False) if attest is None else bool(attest)
    profile_id = proof_profile_id or defaults.get("proof_profile") or defaults.get(
        "proof_profile_id"
    )
    if profile_id:
        profile_id = str(profile_id).strip() or None

    if resume_state:
        context: Dict[str, Any] = dict(resume_state.get("context") or {})
        if input_text is not None:
            context["input_text"] = input_text
        if upload_id is not None:
            context["upload_id"] = upload_id
        if llm is not None:
            context["llm"] = llm
        trace_steps: List[Dict[str, Any]] = list(resume_state.get("run_trace_steps") or [])
        previous_status = resume_state.get("previous_step_status")
        seed_ids = resume_state.get("next_step_ids")
        if not seed_ids and resume_state.get("approve_step_id"):
            seed_ids = [resume_state["approve_step_id"]]
        if not seed_ids and "next_step_index" in resume_state:
            idx = int(resume_state["next_step_index"])
            steps_tmp = doc.get("steps") or []
            if 0 <= idx < len(steps_tmp):
                seed_ids = [steps_tmp[idx]["id"]]
        if not seed_ids:
            seed_ids = _entry_step_ids(doc)
    else:
        if input_text is None:
            input_text = (
                "Contact John at john.doe@example.com or call (555) 123-4567. "
                "SSN: 123-45-6789. Card: 4111 1111 1111 1111."
            )
        context = {
            "input_text": input_text,
            "upload_id": upload_id,
            "llm": llm,
            "artifacts": [],
            "pipeline_id": doc["id"],
            "parent_run": parent_run,
        }
        trace_steps = []
        previous_status = None
        seed_ids = _entry_step_ids(doc)

    steps = doc["steps"]
    step_by_id = {s["id"]: s for s in steps}
    final_status = "succeeded"
    fatal_error: Optional[str] = None
    pause_info: Optional[Dict[str, Any]] = None
    visited: Set[str] = set()
    queue: deque[str] = deque(seed_ids)

    if not resume_state:
        runtime.system_audit.log_event(
            event_type="pipeline_run_started",
            data={
                "pipeline_id": doc["id"],
                "pipeline_version": doc["version"],
                "step_count": len(steps),
                "attest": want_attest,
                "edge_count": len(doc.get("edges") or []),
            },
        )

    while queue:
        step_id = queue.popleft()
        step = step_by_id.get(step_id)
        if not step:
            continue
        if step_id in visited:
            final_status = "failed"
            fatal_error = f"cycle detected at step {step_id}"
            break
        visited.add(step_id)

        def _enqueue_after(status: str) -> None:
            if status == "succeeded":
                for nxt in _successors(doc, step_id, kinds=("success", "always")):
                    if nxt not in visited:
                        queue.append(nxt)
            elif status == "failed":
                fails = _successors(doc, step_id, kinds=("failure",))
                for nxt in fails:
                    if nxt not in visited:
                        queue.append(nxt)
            elif status == "skipped":
                for nxt in _successors(doc, step_id, kinds=("success", "always")):
                    if nxt not in visited:
                        queue.append(nxt)

        if step.get("enabled") is False:
            entry = {
                "step_id": step_id,
                "name": step.get("name"),
                "uses": step.get("uses"),
                "status": "skipped",
                "started_at": None,
                "finished_at": None,
                "error": None,
                "artifact_refs": [],
                "summary": {"reason": "step disabled (enabled=false)"},
            }
            trace_steps.append(entry)
            previous_status = "skipped"
            _enqueue_after("skipped")
            continue

        when = step.get("when") or "always"
        if when == "previous_succeeded" and previous_status not in (
            None,
            "succeeded",
            "skipped",
        ):
            entry = {
                "step_id": step_id,
                "name": step.get("name"),
                "uses": step.get("uses"),
                "status": "skipped",
                "started_at": None,
                "finished_at": None,
                "error": None,
                "artifact_refs": [],
                "summary": {"reason": "when=previous_succeeded not met"},
            }
            trace_steps.append(entry)
            previous_status = "skipped"
            _enqueue_after("skipped")
            continue
        if when == "previous_failed" and previous_status != "failed":
            entry = {
                "step_id": step_id,
                "name": step.get("name"),
                "uses": step.get("uses"),
                "status": "skipped",
                "started_at": None,
                "finished_at": None,
                "error": None,
                "artifact_refs": [],
                "summary": {"reason": "when=previous_failed not met"},
            }
            trace_steps.append(entry)
            previous_status = "skipped"
            _enqueue_after("skipped")
            continue

        entry = {
            "step_id": step_id,
            "name": step.get("name"),
            "uses": step.get("uses"),
            "status": "running",
            "started_at": _utcnow(),
            "finished_at": None,
            "error": None,
            "artifact_refs": [],
            "summary": {},
            "pack_profile": step.get("pack_profile"),
        }
        on_failure = step.get("on_failure") or default_fail
        try:
            binding = parse_uses(step["uses"])
            config = dict(step.get("config") or {})
            if step.get("capabilities_required"):
                config["capabilities_required"] = step["capabilities_required"]

            if binding["kind"] == "approve":
                if auto_approve or (
                    resume_state
                    and resume_state.get("approve_step_id") == step_id
                ):
                    output = {
                        "approved": True,
                        "approved_at": _utcnow(),
                        "note": config.get("note") or "operator approved",
                    }
                    context["last_output"] = output
                    entry["status"] = "succeeded"
                    entry["summary"] = output
                    entry["finished_at"] = _utcnow()
                    trace_steps.append(entry)
                    previous_status = "succeeded"
                    if resume_state:
                        resume_state = None
                    _enqueue_after("succeeded")
                    continue
                entry["status"] = "awaiting_approval"
                entry["finished_at"] = _utcnow()
                entry["summary"] = {
                    "message": config.get("message") or "Awaiting operator approval"
                }
                trace_steps.append(entry)
                final_status = "awaiting_approval"
                pause_info = {
                    "step_id": step_id,
                    "message": config.get("message") or "Awaiting operator approval",
                    "resume_state": {
                        "next_step_ids": [step_id],
                        "approve_step_id": step_id,
                        "context": _serializable_context(context),
                        "run_trace_steps": trace_steps,
                        "previous_step_status": previous_status,
                        "document": doc,
                        "want_attest": want_attest,
                    },
                }
                break

            with pack_profile_context(runtime.base_path, step.get("pack_profile")):
                if binding["kind"] == "agent":
                    output = _run_agent_step(
                        agent_id=binding["agent_id"],
                        runtime=runtime,
                        context=context,
                        config=config,
                    )
                elif binding["kind"] == "pack":
                    output = _run_pack_step(
                        pack_id=binding["pack_id"],
                        runtime=runtime,
                        context=context,
                    )
                elif binding["kind"] == "attest":
                    output = _run_attest_step(runtime=runtime, context=context)
                elif binding["kind"] == "handoff":
                    output = _run_handoff_step(
                        runtime=runtime, context=context, config=config
                    )
                elif binding["kind"] == "loop":
                    output = _run_loop_step(
                        runtime=runtime, context=context, config=config
                    )
                else:
                    raise PipelineSpecError(f"unsupported binding {binding}")

            entry["status"] = "succeeded"
            entry["summary"] = _summarize_output(output)
            if isinstance(output, dict):
                for ref_key in (
                    "artifact_hash",
                    "attestation_id",
                    "full_provenance_hash",
                ):
                    if output.get(ref_key):
                        entry["artifact_refs"].append({ref_key: output[ref_key]})
            entry["finished_at"] = _utcnow()
            trace_steps.append(entry)
            previous_status = "succeeded"
            _enqueue_after("succeeded")
        except Exception as exc:
            entry["status"] = "failed"
            entry["error"] = str(exc)
            entry["finished_at"] = _utcnow()
            trace_steps.append(entry)
            previous_status = "failed"
            fail_next = _successors(doc, step_id, kinds=("failure",))
            if fail_next:
                _enqueue_after("failed")
                continue
            if on_failure == "continue":
                _enqueue_after("succeeded")  # continue along success path
                continue
            final_status = "failed"
            fatal_error = str(exc)
            break

    if final_status != "awaiting_approval":
        finished_ids = {t["step_id"] for t in trace_steps}
        for step in steps:
            if step["id"] not in finished_ids:
                trace_steps.append(
                    {
                        "step_id": step["id"],
                        "name": step.get("name"),
                        "uses": step.get("uses"),
                        "status": "skipped",
                        "started_at": None,
                        "finished_at": None,
                        "error": None,
                        "artifact_refs": [],
                        "summary": {"reason": "not reached by graph"},
                    }
                )

    attest_meta = {
        "requested": want_attest,
        "completed": bool(context.get("attest_completed")),
    }
    if (
        want_attest
        and final_status == "succeeded"
        and not context.get("attest_completed")
    ):
        try:
            if context.get("attested_result"):
                _run_attest_step(runtime=runtime, context=context)
                attest_meta["completed"] = True
            else:
                attest_meta["error"] = "no attested_result to attest"
        except Exception as exc:
            attest_meta["error"] = str(exc)
            final_status = "failed"
            fatal_error = str(exc)

    # If proof profile requires attest but run didn't request it, still fail-closed later
    # via missing ZK predicates — or auto-attest when profile.require_attest.
    if profile_id and final_status == "succeeded" and not context.get("attest_completed"):
        try:
            from .proof_studio import load_proof_spec

            _spec = load_proof_spec(runtime.base_path, profile_id)
            if _spec.get("require_attest") and context.get("attested_result"):
                _run_attest_step(runtime=runtime, context=context)
                attest_meta["completed"] = True
                attest_meta["requested"] = True
                attest_meta["via"] = "proof_profile.require_attest"
        except Exception as exc:
            attest_meta["proof_profile_attest_error"] = str(exc)

    attested = context.get("attested_result")
    proof_claim: Optional[Dict[str, Any]] = None
    if profile_id and final_status == "succeeded":
        from .proof_studio import apply_proof_profile_to_result

        preliminary = {
            "final_status": final_status,
            "error": fatal_error,
            "attested_result": attested,
            "zk_summary": context.get("zk_summary"),
        }
        preliminary = apply_proof_profile_to_result(
            runtime.base_path,
            preliminary,
            profile_id,
            zk_summary=context.get("zk_summary"),
        )
        proof_claim = preliminary.get("proof_claim")
        final_status = preliminary.get("final_status") or final_status
        fatal_error = preliminary.get("error") or fatal_error
        attested = preliminary.get("attested_result") or attested
        if isinstance(attested, dict) and proof_claim is not None:
            attested["proof_claim"] = proof_claim
            context["attested_result"] = attested

    write_meta = None
    if isinstance(attested, dict) and final_status == "succeeded":
        name = "attested_result_composition"
        if attest_meta.get("completed"):
            name = "attested_result_composition_with_zk"
        write_meta = runtime.provider.write_artifact(artifact=attested, name=name)

    runtime.system_audit.log_event(
        event_type=(
            "pipeline_run_awaiting_approval"
            if final_status == "awaiting_approval"
            else "pipeline_run_completed"
        ),
        data={
            "pipeline_id": doc["id"],
            "final_status": final_status,
            "attest": attest_meta,
            "proof_profile": profile_id,
            "proof_claim_ok": (proof_claim or {}).get("ok") if proof_claim else None,
            "artifact_hash": (write_meta or {}).get("hash"),
            "handoffs": context.get("handoffs"),
        },
    )

    result_body: Dict[str, Any] = {
        "pipeline_id": doc["id"],
        "pipeline_version": doc["version"],
        "pipeline_name": doc.get("name"),
        "final_status": final_status,
        "error": fatal_error,
        "run_trace": {
            "pipeline_id": doc["id"],
            "pipeline_version": doc["version"],
            "steps": trace_steps,
            "final_status": final_status,
            "attest": attest_meta,
            "proof_profile": profile_id,
        },
        "attest": attest_meta,
        "zk_summary": context.get("zk_summary"),
        "proof_profile": profile_id,
        "proof_claim": proof_claim,
        "attestation_id": (attested or {}).get("attestation_id")
        if isinstance(attested, dict)
        else None,
        "governance_decision": (
            (attested or {}).get("governance_decision", {}).get("decision")
            if isinstance(attested, dict)
            else None
        ),
        "artifact_hash": (write_meta or {}).get("hash"),
        "artifact_path": (write_meta or {}).get("path"),
        "attested_result": attested if final_status == "succeeded" else attested,
        "last_output_summary": _summarize_output(context.get("last_output")),
        "handoffs": context.get("handoffs"),
        "pause": pause_info,
    }
    return result_body


def run_stored_pipeline(
    pipeline_id: str,
    *,
    runtime: Optional[APXRuntime] = None,
    input_text: Optional[str] = None,
    upload_id: Optional[str] = None,
    attest: Optional[bool] = None,
    llm: Optional[Dict[str, Any]] = None,
    resume_state: Optional[Dict[str, Any]] = None,
    auto_approve: bool = False,
    parent_run: Optional[Dict[str, Any]] = None,
    proof_profile_id: Optional[str] = None,
) -> Dict[str, Any]:
    runtime = runtime or APXRuntime()
    try:
        doc = load_pipeline(runtime.base_path, pipeline_id)
    except PipelineStoreError as exc:
        raise PipelineSpecError(str(exc)) from exc
    return run_pipeline_document(
        doc,
        runtime=runtime,
        input_text=input_text,
        upload_id=upload_id,
        attest=attest,
        llm=llm,
        resume_state=resume_state,
        auto_approve=auto_approve,
        parent_run=parent_run,
        proof_profile_id=proof_profile_id,
    )


def resume_pipeline_approval(
    *,
    runtime: APXRuntime,
    resume_state: Dict[str, Any],
    approved: bool = True,
    note: str = "",
) -> Dict[str, Any]:
    """Continue a paused pipeline after operator approval."""
    doc = resume_state.get("document")
    if not isinstance(doc, dict):
        raise PipelineSpecError("resume_state missing document")
    if not approved:
        return {
            "pipeline_id": doc.get("id"),
            "final_status": "failed",
            "error": note or "operator rejected approval",
            "run_trace": {
                "pipeline_id": doc.get("id"),
                "steps": resume_state.get("run_trace_steps") or [],
                "final_status": "failed",
            },
        }
    # Mark approve step for auto-pass
    state = copy.deepcopy(resume_state)
    state["approve_step_id"] = resume_state.get("approve_step_id")
    return run_pipeline_document(
        doc,
        runtime=runtime,
        resume_state=state,
        auto_approve=False,  # uses approve_step_id match
        attest=resume_state.get("want_attest"),
    )
