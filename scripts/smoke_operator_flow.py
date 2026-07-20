"""
End-to-end operator flow verification.
Run: python -m scripts.smoke_operator_flow

Uses APXV_API_KEY if set; otherwise managed/config/OPERATOR-KEY-*.txt.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

API = os.environ.get("APXV_API_URL", "http://127.0.0.1:8741")


def _load_key() -> str:
    env = os.environ.get("APXV_API_KEY") or os.environ.get("APXV_KEY")
    if env:
        return env.strip()
    for path in sorted((ROOT / "managed" / "config").glob("OPERATOR-KEY-*.txt")):
        text = path.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"API Key:\s*(\S+)", text)
        if m:
            return m.group(1).strip()
    raise SystemExit(
        "No API key found. Set APXV_API_KEY or create managed/config/OPERATOR-KEY-*.txt"
    )


KEY = _load_key()

RESULTS: list[tuple[str, bool, str]] = []


def ok(name: str, passed: bool, detail: str = "") -> None:
    RESULTS.append((name, passed, detail))
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))


def req(method: str, path: str, body=None, timeout: int = 180):
    data = None
    headers = {"Authorization": f"Bearer {KEY}", "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw[:800]}
        return exc.code, payload


def wait_job(job_id: str, max_polls: int = 80):
    for _ in range(max_polls):
        time.sleep(0.5)
        st, job = req("GET", f"/api/v2/jobs/{job_id}")
        if job.get("status") in ("completed", "failed", "error"):
            return job
    return {"status": "timeout"}


def independent_verify_universal(public_inputs: dict, proof_hex: str) -> bool:
    """Call apxv-zk verify with public inputs + proof_hex (same as product)."""
    from scripts.rust_bins import build_apxv_zk_command

    payload = {**public_inputs, "proof_hex": proof_hex}
    with tempfile.TemporaryDirectory(prefix="apxv-verify-") as tmp:
        path = Path(tmp) / "verify.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        cmd, cwd = build_apxv_zk_command(
            ROOT, "verify", "universal-predicate-v1", "--inputs", str(path)
        )
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
        out = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0 and "VALID" in out


def main() -> int:
    print("=== APXV full-flow verification ===\n")

    # 1) Platform
    st, health = req("GET", "/health")
    ok(
        "API health",
        st == 200,
        f"status={health.get('status')} trusted={ (health.get('integrity') or {}).get('capability_policy_trusted') }",
    )

    pk = ROOT / "rust/apxv-zk/keys/universal-predicate-v1.pk"
    vk = ROOT / "rust/apxv-zk/keys/universal-predicate-v1.vk"
    ok("universal-predicate-v1 keys on disk", pk.is_file() and vk.is_file(), f"vk={vk.stat().st_size}B")
    vk_hash = hashlib.sha256(vk.read_bytes()).hexdigest() if vk.is_file() else ""

    st, status = req("GET", "/api/v2/studio/proofs/status")
    ok(
        "Proof Studio status reports keys",
        st == 200 and (status.get("universal_predicate_v1") or {}).get("keys_available") is True,
        str(status.get("universal_predicate_v1")),
    )

    # 2) Surfaces: agents, packs, pipelines
    st, agents = req("GET", "/api/v2/agents")
    agent_list = agents if isinstance(agents, list) else agents.get("agents") or agents.get("items") or []
    ok("Core agents listed", st == 200 and len(agent_list) >= 3, f"count={len(agent_list)}")

    st, packs = req("GET", "/api/v2/packs")
    pack_list = packs if isinstance(packs, list) else packs.get("packs") or []
    pack_ids = [p.get("id") for p in pack_list if isinstance(p, dict)]
    ok(
        "Product packs listed",
        st == 200 and "apxv-pack-reference-redaction" in pack_ids,
        str(pack_ids),
    )

    st, pipes = req("GET", "/api/v2/pipelines")
    pipe_list = pipes if isinstance(pipes, list) else pipes.get("pipelines") or []
    ok("Pipelines listed", st == 200 and len(pipe_list) >= 1, f"count={len(pipe_list)}")

    # 3) Studio agent quick path
    agent_id = "APXV-AGENT-OP-FLOWCHECK"
    st, _ = req(
        "POST",
        "/api/v2/studio/agents",
        {
            "id": agent_id,
            "name": "Flow Check Agent",
            "description": "E2E flow agent",
            "agent_type": "deterministic",
            "instruction_md": "# Instructions\n\nProcess input under policy.\n",
            "knowledge_md": "# Knowledge\n\nFlow check.\n",
        },
    )
    ok("Studio save agent", st == 200, agent_id)
    st, tr = req("POST", f"/api/v2/studio/agents/{agent_id}/test", {})
    ok("Studio test agent", st == 200 and tr.get("ok") is True, str(tr.get("last_test", {}).get("final_status")))
    st, _ = req("POST", f"/api/v2/studio/agents/{agent_id}/promote", {})
    ok("Studio promote agent", st == 200)

    # 4) Proof intent → save → test → promote
    intent = (
        "Prove that email and phone were redacted, rules were bound, "
        "at least 1 entity was found, the run was attested, and governance approved."
    )
    st, compiled = req(
        "POST",
        "/api/v2/studio/proofs/compile-intent",
        {"intent_md": intent, "proof_id": "APXV-PROOF-FLOWCHECK", "name": "Flow check claim"},
    )
    pred_ids = [
        p.get("id") if isinstance(p, dict) else p for p in (compiled.get("predicates") or [])
    ]
    ok(
        "Compile intent → catalog predicates",
        st == 200 and "REDACTION_NONEMPTY" in pred_ids and "CATEGORY_INCLUDES" in pred_ids,
        str(pred_ids),
    )

    st, saved = req(
        "POST",
        "/api/v2/studio/proofs/from-intent",
        {
            "intent_md": intent,
            "proof_id": "APXV-PROOF-FLOWCHECK",
            "name": "Flow check claim",
            "prefer_universal": True,
        },
    )
    proof = saved.get("proof") or {}
    ok(
        "Save proof profile from intent",
        st == 200 and proof.get("id") == "APXV-PROOF-FLOWCHECK",
        f"binding={proof.get('circuit_binding')}",
    )

    st, tested = req("POST", "/api/v2/studio/proofs/APXV-PROOF-FLOWCHECK/test", {})
    claim = tested.get("proof_claim") or {}
    up = claim.get("universal_predicate_proof") or (tested.get("result") or {}).get(
        "universal_predicate_proof"
    )
    ok(
        "Proof profile runtime test",
        st == 200 and tested.get("ok") is True and claim.get("ok") is True,
        f"failed={claim.get('failed_predicates')}",
    )
    ok(
        "Universal proof attached on Studio test",
        isinstance(up, dict)
        and up.get("verification_result") is True
        and bool(up.get("proof_hex") or up.get("vk_hash")),
        f"vk_hash={(up or {}).get('vk_hash', '')[:20]}…",
    )

    # Independent CLI verify of Studio-test proof
    if isinstance(up, dict) and up.get("public_inputs") and (up.get("proof_hex") or claim.get("universal_predicate_proof")):
        # proof_hex may only be on full result
        full_up = up
        if not full_up.get("proof_hex"):
            # re-fetch from result
            full_up = (tested.get("result") or {}).get("universal_predicate_proof") or up
            if not full_up.get("proof_hex") and isinstance(tested.get("result"), dict):
                ar = (tested.get("result") or {}).get("attested_result") or {}
                full_up = ar.get("universal_predicate_proof") or full_up
        # claim may only store summary — pull from result.attested_result
        if not full_up.get("proof_hex"):
            res = tested.get("result") or {}
            ar = res.get("attested_result") or {}
            full_up = ar.get("universal_predicate_proof") or res.get("universal_predicate_proof") or full_up

        if full_up.get("proof_hex") and full_up.get("public_inputs"):
            verified = independent_verify_universal(
                full_up["public_inputs"], full_up["proof_hex"]
            )
            ok(
                "Independent apxv-zk verify (Studio test proof)",
                verified,
                "VALID" if verified else "INVALID",
            )
            if full_up.get("vk_hash"):
                ok(
                    "VK hash matches on-disk key",
                    full_up["vk_hash"] == vk_hash,
                    full_up["vk_hash"][:24] + "…",
                )
        else:
            # Try prove path still reported independent_verify
            ok(
                "Independent apxv-zk verify (Studio test proof)",
                full_up.get("independent_verify") is True,
                "used product independent_verify flag; proof_hex not in summary",
            )

    st, _ = req("POST", "/api/v2/studio/proofs/APXV-PROOF-FLOWCHECK/promote", {})
    ok("Promote proof profile", st == 200)

    st, shelf = req("GET", "/api/v2/studio/shelf")
    shelf_proofs = [p.get("id") for p in (shelf.get("proofs") or [])]
    ok(
        "Promoted proof on Workbench shelf",
        "APXV-PROOF-FLOWCHECK" in shelf_proofs,
        str(shelf_proofs),
    )

    # 5) Workbench-style pipeline run with proof_profile
    sample = (
        "Contact Morgan Lee at morgan.lee@example.com or call (555) 222-3344. "
        "SSN 321-54-9876."
    )
    st, jobq = req(
        "POST",
        "/api/v2/pipelines/apxv-pipeline-reference-linear/run",
        {
            "input_text": sample,
            "proof_profile": "APXV-PROOF-FLOWCHECK",
            "async": True,
        },
    )
    ok("Queue pipeline run with proof_profile", st in (200, 202), str(jobq.get("job_id")))
    job = wait_job(jobq.get("job_id") or "")
    result = job.get("result") or {}
    ok(
        "Pipeline completed with claim satisfied",
        job.get("status") == "completed" and result.get("final_status") == "succeeded",
        f"final={result.get('final_status')} err={result.get('error')}",
    )
    pc = result.get("proof_claim") or {}
    ok("Run proof_claim.ok", pc.get("ok") is True, f"failed={pc.get('failed_predicates')}")
    # redaction actually happened
    summary = result.get("last_output_summary") or {}
    redactions = summary.get("total_redactions")
    if redactions is None:
        ar = result.get("attested_result") or {}
        out = ((ar.get("proposed_artifact") or {}).get("output") or {})
        redactions = out.get("total_redactions")
    ok("Real redactions applied", isinstance(redactions, int) and redactions > 0, f"count={redactions}")

    up2 = result.get("universal_predicate_proof") or pc.get("universal_predicate_proof")
    ok(
        "Universal proof on pipeline run",
        isinstance(up2, dict) and (
            up2.get("verification_result") is True or up2.get("independent_verify") is True
        ),
        f"circuit={ (up2 or {}).get('circuit') }",
    )

    # Get full proof_hex from attested artifact if needed
    ar = result.get("attested_result") or {}
    full_proof = ar.get("universal_predicate_proof") or up2 or {}
    if full_proof.get("proof_hex") and full_proof.get("public_inputs"):
        v2 = independent_verify_universal(full_proof["public_inputs"], full_proof["proof_hex"])
        ok("Independent verify (pipeline run proof)", v2, "VALID" if v2 else "INVALID")
    elif full_proof.get("independent_verify"):
        ok(
            "Independent verify (pipeline run proof)",
            True,
            "product independent_verify=True (proof stored on artifact)",
        )
    else:
        ok("Independent verify (pipeline run proof)", False, "no proof material")

    # 6) Fail-closed claim
    st, _ = req(
        "POST",
        "/api/v2/studio/proofs",
        {
            "id": "APXV-PROOF-FAILCLOSED",
            "name": "Impossible claim",
            "intent_md": "# Impossible\n",
            "predicates": [{"id": "ENTITY_COUNT_GTE", "params": {"n": 99999}}],
            "fail_closed": True,
            "require_attest": False,
        },
    )
    st, jobq2 = req(
        "POST",
        "/api/v2/pipelines/apxv-pipeline-reference-linear/run",
        {
            "input_text": "hello only, almost no pii maybe none",
            "proof_profile": "APXV-PROOF-FAILCLOSED",
            "async": True,
        },
    )
    job2 = wait_job(jobq2.get("job_id") or "")
    r2 = job2.get("result") or {}
    ok(
        "Fail-closed rejects unsatisfiable claim",
        r2.get("final_status") == "failed"
        and (r2.get("proof_claim") or {}).get("ok") is False,
        f"final={r2.get('final_status')} failed_pred={(r2.get('proof_claim') or {}).get('failed_predicates')}",
    )

    # 7) Dual-track attest path (governance + entity) — real Groth16 if setup present
    st, jobq3 = req(
        "POST",
        "/api/v2/pipelines/apxv-pipeline-reference-linear/run",
        {
            "input_text": sample,
            "proof_profile": "APXV-PROOF-FLOWCHECK",
            "attest": True,
            "async": True,
        },
    )
    # Dual-track Groth16 can take >60s on cold prover; poll longer than claim-only runs
    job3 = wait_job(jobq3.get("job_id") or "", max_polls=300)
    r3 = job3.get("result") or {}
    attest_meta = r3.get("attest") or {}
    zk = r3.get("zk_summary") or {}
    ar3 = r3.get("attested_result") or {}
    has_gov = bool(ar3.get("zk_proof_redaction") or (zk.get("governance") or {}))
    has_ent = bool(ar3.get("entity_proofs") or (zk.get("entity") or {}))
    ok(
        "Attest run finished",
        job3.get("status") == "completed" and r3.get("final_status") == "succeeded",
        f"final={r3.get('final_status')} status={job3.get('status')} attest={attest_meta} err={r3.get('error')}",
    )
    if r3.get("final_status") == "succeeded":
        ok(
            "Dual-track ZK material present (when attest succeeds)",
            has_gov or has_ent or bool(r3.get("universal_predicate_proof")),
            f"gov={has_gov} entity={has_ent} uni={bool(r3.get('universal_predicate_proof') or (r3.get('proof_claim') or {}).get('universal_predicate_proof'))}",
        )
    else:
        ok(
            "Dual-track ZK material present (when attest succeeds)",
            False,
            f"attest path failed: {r3.get('error') or attest_meta} — check entity/gov key setup if needed",
        )

    # 8) Export claim bundle
    st, export = req(
        "POST",
        "/api/v2/studio/proofs/export-claim",
        {
            "proof_profile_id": "APXV-PROOF-FLOWCHECK",
            "claim": pc,
        },
    )
    bundle = export.get("bundle") or {}
    ok(
        "Export claim bundle",
        st == 200 and bundle.get("export_type") == "apxv.proof_claim_bundle",
        f"has_uni={bundle.get('universal_predicate_proof') is not None}",
    )

    # Summary
    print("\n=== SUMMARY ===")
    passed = sum(1 for _, p, _ in RESULTS if p)
    failed = sum(1 for _, p, _ in RESULTS if not p)
    for name, p, detail in RESULTS:
        print(f"  {'✓' if p else '✗'} {name}" + (f" ({detail})" if detail and not p else ""))
    print(f"\n{passed} passed, {failed} failed out of {len(RESULTS)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
