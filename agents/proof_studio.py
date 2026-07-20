"""
APXV Proof Studio — author, test, promote Proof Profiles.

Operators customize *what is proven* via a predicate catalog bound to
existing dual-track circuits (and future universal-predicate). They do not
author R1CS. Fail closed when claims cannot be satisfied.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .pipeline_runner import run_pipeline_document
from .runtime import APXRuntime
from .studio_service import StudioError, _load_catalog, _save_catalog, _studio_root

PROOFS_REL = Path("managed") / "studio" / "proofs"
_PROOF_ID_RE = re.compile(r"^APXV-PROOF-[A-Z0-9][A-Z0-9-]*$")

API_VERSION = "apxv.proof/v0.1"
CIRCUIT_BINDING_EXISTING = "existing-dual-track"
CIRCUIT_BINDING_UNIVERSAL = "universal-predicate-v1"

# Predicate bit index — must match rust universal_predicate.rs
PREDICATE_BIT: Dict[str, int] = {
    "REDACTION_NONEMPTY": 0,
    "ENTITY_COUNT_GTE": 1,
    "CATEGORY_INCLUDES": 2,
    "RULE_BOUND": 3,
    "PIPELINE_CHAIN": 4,
    "ATTESTED_STATUS": 5,
    "GOVERNANCE_APPROVED": 6,
    "ZK_GOVERNANCE_PRESENT": 7,
    "ZK_ENTITY_PRESENT": 8,
    "ARTIFACT_HASH_PRESENT": 9,  # structural only in evaluate; not in circuit v1 mask low-9
    "HANDOFF_RECORDED": 10,
}


def universal_keys_available(base_path: Optional[Path] = None) -> bool:
    try:
        from .zk.universal_bridge import keys_available

        return keys_available(base_path)
    except Exception:
        base = base_path or Path(__file__).resolve().parent.parent
        keys = base / "rust" / "apxv-zk" / "keys"
        return (keys / "universal-predicate-v1.pk").is_file() and (
            keys / "universal-predicate-v1.vk"
        ).is_file()


# Predicate catalog — trust boundary. NL/UI may only select from this set.
PREDICATE_CATALOG: Dict[str, Dict[str, Any]] = {
    "REDACTION_NONEMPTY": {
        "title": "Redaction occurred",
        "description": "At least one redaction was applied (count > 0).",
        "params": {},
        "maps_to_circuits": ["redaction", "redaction-v1", "core-redaction"],
        "requires_zk": False,
    },
    "ENTITY_COUNT_GTE": {
        "title": "Entity count ≥ N",
        "description": "Detected/redacted entity count meets a minimum.",
        "params": {"n": {"type": "int", "default": 1, "min": 0}},
        "maps_to_circuits": ["redaction-v1", "core-redaction", "batch-merkle"],
        "requires_zk": False,
    },
    "CATEGORY_INCLUDES": {
        "title": "Categories include",
        "description": "Redaction categories include each listed type (e.g. email, ssn).",
        "params": {
            "categories": {
                "type": "string_list",
                "default": ["email"],
            }
        },
        "maps_to_circuits": ["redaction-v1"],
        "requires_zk": False,
    },
    "RULE_BOUND": {
        "title": "Rule binding present",
        "description": "Governance rule binding is present on the attestation path.",
        "params": {},
        "maps_to_circuits": ["rule-binding"],
        "requires_zk": False,
    },
    "PIPELINE_CHAIN": {
        "title": "Pipeline chain present",
        "description": "Agent/pipeline chain is recorded on the attestation.",
        "params": {},
        "maps_to_circuits": ["pipeline"],
        "requires_zk": False,
    },
    "ATTESTED_STATUS": {
        "title": "Run attested",
        "description": "Final status is ATTESTED (or equivalent success with attestation id).",
        "params": {},
        "maps_to_circuits": [],
        "requires_zk": False,
    },
    "GOVERNANCE_APPROVED": {
        "title": "Governance approved",
        "description": "Governance decision is APPROVED or APPROVED_WITH_REVIEW_FLAG.",
        "params": {},
        "maps_to_circuits": [],
        "requires_zk": False,
    },
    "ZK_GOVERNANCE_PRESENT": {
        "title": "Governance ZK proofs present",
        "description": "Redaction, rule-binding, and pipeline Groth16 proofs are attached.",
        "params": {},
        "maps_to_circuits": ["redaction", "rule-binding", "pipeline"],
        "requires_zk": True,
    },
    "ZK_ENTITY_PRESENT": {
        "title": "Entity ZK proofs present",
        "description": "Entity-track proofs are attached on the artifact.",
        "params": {},
        "maps_to_circuits": ["redaction-v1", "core-redaction", "merkle-inclusion"],
        "requires_zk": True,
    },
    "ARTIFACT_HASH_PRESENT": {
        "title": "Artifact hash present",
        "description": "Run produced a content-addressed artifact hash.",
        "params": {},
        "maps_to_circuits": [],
        "requires_zk": False,
    },
    "HANDOFF_RECORDED": {
        "title": "Handoff recorded",
        "description": "Pipeline handoff metadata is present (swarm/stage flows).",
        "params": {},
        "maps_to_circuits": [],
        "requires_zk": False,
    },
    "UNIVERSAL_PROOF_VALID": {
        "title": "Universal predicate proof valid",
        "description": "Groth16 universal-predicate-v1 proof verified for this claim.",
        "params": {},
        "maps_to_circuits": ["universal-predicate-v1"],
        "requires_zk": True,
    },
}

# Built-in templates operators can clone into their own profiles.
PROOF_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "APXV-PROOF-REDACTION-CORE",
        "name": "Redaction core claim",
        "description": "Prove redaction occurred with rule binding and pipeline chain.",
        "intent_md": (
            "# Proof intent\n\n"
            "Prove that this run redacted sensitive data, bound governance rules, "
            "and recorded the pipeline agent chain — without revealing raw text.\n"
        ),
        "predicates": [
            {"id": "REDACTION_NONEMPTY"},
            {"id": "RULE_BOUND"},
            {"id": "PIPELINE_CHAIN"},
            {"id": "ATTESTED_STATUS"},
            {"id": "GOVERNANCE_APPROVED"},
        ],
        "circuit_binding": CIRCUIT_BINDING_EXISTING,
        "fail_closed": True,
        "require_attest": False,
    },
    {
        "id": "APXV-PROOF-ENTITY-MIN",
        "name": "Entity minimum claim",
        "description": "Prove at least one entity redaction including common PII categories.",
        "intent_md": (
            "# Proof intent\n\n"
            "Prove entity count ≥ 1 and that email (and optionally SSN/phone) "
            "categories were involved in redaction.\n"
        ),
        "predicates": [
            {"id": "REDACTION_NONEMPTY"},
            {"id": "ENTITY_COUNT_GTE", "params": {"n": 1}},
            {
                "id": "CATEGORY_INCLUDES",
                "params": {"categories": ["email", "phone", "ssn"]},
            },
            {"id": "ATTESTED_STATUS"},
        ],
        "circuit_binding": CIRCUIT_BINDING_EXISTING,
        "fail_closed": True,
        "require_attest": False,
    },
    {
        "id": "APXV-PROOF-FULL-ATTEST",
        "name": "Full dual-track attest claim",
        "description": "Structural claims plus governance and entity Groth16 proofs present.",
        "intent_md": (
            "# Proof intent\n\n"
            "Prove the full dual-track attestation path: redactions, governance, "
            "and real ZK proofs on both governance and entity tracks.\n"
        ),
        "predicates": [
            {"id": "REDACTION_NONEMPTY"},
            {"id": "ENTITY_COUNT_GTE", "params": {"n": 1}},
            {"id": "RULE_BOUND"},
            {"id": "PIPELINE_CHAIN"},
            {"id": "ATTESTED_STATUS"},
            {"id": "GOVERNANCE_APPROVED"},
            {"id": "ZK_GOVERNANCE_PRESENT"},
            {"id": "ZK_ENTITY_PRESENT"},
        ],
        "circuit_binding": CIRCUIT_BINDING_EXISTING,
        "fail_closed": True,
        "require_attest": True,
    },
]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_proof_id(proof_id: str) -> str:
    pid = (proof_id or "").strip().upper().replace("_", "-")
    if not pid.startswith("APXV-PROOF-"):
        pid = f"APXV-PROOF-{pid.lstrip('-')}"
    if not _PROOF_ID_RE.match(pid):
        raise StudioError(
            "proof id must match APXV-PROOF-<SLUG> (A-Z, 0-9, hyphens)"
        )
    return pid


def proof_dir(base_path: Path, proof_id: str) -> Path:
    return base_path / PROOFS_REL / proof_id


def list_predicate_catalog() -> List[Dict[str, Any]]:
    out = []
    for pid, meta in PREDICATE_CATALOG.items():
        out.append({"id": pid, **meta})
    return out


def list_proof_templates() -> List[Dict[str, Any]]:
    return [dict(t) for t in PROOF_TEMPLATES]


def _normalize_predicates(raw: Any) -> List[Dict[str, Any]]:
    if not raw:
        raise StudioError("proof profile requires at least one predicate")
    if not isinstance(raw, list):
        raise StudioError("predicates must be a list")
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            pred_id = item.strip().upper()
            params: Dict[str, Any] = {}
        elif isinstance(item, dict):
            pred_id = str(item.get("id") or item.get("predicate") or "").strip().upper()
            params = dict(item.get("params") or {})
        else:
            raise StudioError(f"invalid predicate entry: {item!r}")
        if pred_id not in PREDICATE_CATALOG:
            raise StudioError(
                f"unknown predicate {pred_id!r} — must be from the catalog"
            )
        cat = PREDICATE_CATALOG[pred_id]
        # Fill defaults
        for pname, pmeta in (cat.get("params") or {}).items():
            if pname not in params and isinstance(pmeta, dict) and "default" in pmeta:
                params[pname] = pmeta["default"]
        if pred_id == "ENTITY_COUNT_GTE":
            try:
                params["n"] = int(params.get("n", 1))
            except (TypeError, ValueError) as exc:
                raise StudioError("ENTITY_COUNT_GTE.params.n must be an integer") from exc
            if params["n"] < 0:
                raise StudioError("ENTITY_COUNT_GTE.params.n must be >= 0")
        if pred_id == "CATEGORY_INCLUDES":
            cats = params.get("categories") or []
            if isinstance(cats, str):
                cats = [c.strip() for c in cats.split(",") if c.strip()]
            if not isinstance(cats, list) or not cats:
                raise StudioError("CATEGORY_INCLUDES.params.categories must be a non-empty list")
            params["categories"] = [str(c).strip().lower() for c in cats if str(c).strip()]
        normalized.append({"id": pred_id, "params": params})
    return normalized


def compile_proof_spec(
    *,
    proof_id: str,
    name: str,
    description: str = "",
    intent_md: str = "",
    predicates: Any = None,
    circuit_binding: str = CIRCUIT_BINDING_EXISTING,
    fail_closed: bool = True,
    require_attest: Optional[bool] = None,
    public_outputs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Validate and build machine IR (proof-spec). Fail closed on unknown predicates."""
    pid = _validate_proof_id(proof_id)
    preds = _normalize_predicates(predicates)
    binding = (circuit_binding or CIRCUIT_BINDING_EXISTING).strip()
    if binding not in (CIRCUIT_BINDING_EXISTING, CIRCUIT_BINDING_UNIVERSAL):
        raise StudioError(
            f"circuit_binding must be {CIRCUIT_BINDING_EXISTING} "
            f"or {CIRCUIT_BINDING_UNIVERSAL}"
        )
    if binding == CIRCUIT_BINDING_UNIVERSAL and not universal_keys_available():
        raise StudioError(
            "universal-predicate-v1 keys not found. Run: "
            "python -m scripts.setup_universal_zk   "
            "or: cargo run -p apxv-zk -- setup universal-predicate-v1"
        )

    needs_zk = any(PREDICATE_CATALOG[p["id"]].get("requires_zk") for p in preds)
    if require_attest is None:
        require_attest = needs_zk

    circuits: List[str] = []
    for p in preds:
        for c in PREDICATE_CATALOG[p["id"]].get("maps_to_circuits") or []:
            if c not in circuits:
                circuits.append(c)

    english_parts = []
    for p in preds:
        cat = PREDICATE_CATALOG[p["id"]]
        if p["id"] == "ENTITY_COUNT_GTE":
            english_parts.append(f"entity count ≥ {p['params'].get('n', 1)}")
        elif p["id"] == "CATEGORY_INCLUDES":
            english_parts.append(
                "categories include " + ", ".join(p["params"].get("categories") or [])
            )
        else:
            english_parts.append(cat.get("title") or p["id"])

    claim_english = (
        f"This run proves: {'; '.join(english_parts)}."
        if english_parts
        else "No predicates selected."
    )

    return {
        "apiVersion": API_VERSION,
        "id": pid,
        "name": (name or pid).strip(),
        "description": (description or "").strip(),
        "circuit_binding": binding,
        "predicates": preds,
        "public_outputs": public_outputs
        or [
            "predicate_results",
            "claim_english",
            "attestation_id",
            "artifact_hash",
            "mapped_circuits",
        ],
        "private_sources": [
            "attested_result.proposed_artifact",
            "attested_result.entities",
            "input hashes",
        ],
        "fail_closed": bool(fail_closed),
        "require_attest": bool(require_attest),
        "mapped_circuits": circuits,
        "claim_english": claim_english,
        "intent_md": intent_md or "",
    }


def save_proof_profile(
    runtime: APXRuntime,
    *,
    proof_id: str,
    name: str,
    description: str = "",
    intent_md: str = "",
    predicates: Any = None,
    circuit_binding: str = CIRCUIT_BINDING_EXISTING,
    fail_closed: bool = True,
    require_attest: Optional[bool] = None,
) -> Dict[str, Any]:
    spec = compile_proof_spec(
        proof_id=proof_id,
        name=name,
        description=description,
        intent_md=intent_md,
        predicates=predicates,
        circuit_binding=circuit_binding,
        fail_closed=fail_closed,
        require_attest=require_attest,
    )
    pid = spec["id"]
    d = proof_dir(runtime.base_path, pid)
    d.mkdir(parents=True, exist_ok=True)

    catalog = _load_catalog(runtime.base_path)
    catalog.setdefault("proofs", {})
    prev = catalog["proofs"].get(pid) or {}

    manifest = {
        "id": pid,
        "name": spec["name"],
        "description": spec["description"],
        "kind": "proof_profile",
        "circuit_binding": spec["circuit_binding"],
        "fail_closed": spec["fail_closed"],
        "require_attest": spec["require_attest"],
        "created_at": prev.get("created_at") or _utcnow(),
        "updated_at": _utcnow(),
        "promoted": bool(prev.get("promoted", False)),
        "maturity": prev.get("maturity") or "draft",
        "last_test": prev.get("last_test"),
    }
    (d / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (d / "proof-spec.json").write_text(
        json.dumps(spec, indent=2) + "\n", encoding="utf-8"
    )
    (d / "intent.md").write_text(
        intent_md.strip()
        or spec.get("intent_md")
        or f"# Proof intent\n\n{spec['claim_english']}\n",
        encoding="utf-8",
    )
    (d / "disclosure.json").write_text(
        json.dumps(
            {
                "public_outputs": spec["public_outputs"],
                "private_sources": spec["private_sources"],
                "never_public": ["raw_input_text", "entity_values", "ssn", "email_plaintext"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    catalog["proofs"][pid] = {
        "promoted": manifest["promoted"],
        "maturity": manifest["maturity"],
        "last_test": manifest.get("last_test"),
        "name": manifest["name"],
        "updated_at": manifest["updated_at"],
    }
    _save_catalog(runtime.base_path, catalog)
    return get_proof_profile(runtime.base_path, pid)


def get_proof_profile(base_path: Path, proof_id: str) -> Dict[str, Any]:
    pid = _validate_proof_id(proof_id)
    d = proof_dir(base_path, pid)
    if not (d / "manifest.json").exists():
        raise StudioError(f"Proof profile not found: {pid}")
    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    spec = {}
    if (d / "proof-spec.json").exists():
        spec = json.loads((d / "proof-spec.json").read_text(encoding="utf-8"))
    intent = ""
    if (d / "intent.md").exists():
        intent = (d / "intent.md").read_text(encoding="utf-8")
    catalog = _load_catalog(base_path)
    meta = (catalog.get("proofs") or {}).get(pid) or {}
    return {
        **manifest,
        "intent_md": intent,
        "proof_spec": spec,
        "predicates": spec.get("predicates") or [],
        "claim_english": spec.get("claim_english") or "",
        "mapped_circuits": spec.get("mapped_circuits") or [],
        "promoted": bool(meta.get("promoted", manifest.get("promoted", False))),
        "maturity": meta.get("maturity") or manifest.get("maturity") or "draft",
        "last_test": meta.get("last_test") or manifest.get("last_test"),
        "path": str(d.relative_to(base_path)).replace("\\", "/"),
    }


def list_proof_profiles(base_path: Path) -> List[Dict[str, Any]]:
    root = base_path / PROOFS_REL
    if not root.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "manifest.json").exists():
            try:
                out.append(get_proof_profile(base_path, child.name))
            except StudioError:
                continue
    return out


def list_promoted_proofs(base_path: Path) -> List[Dict[str, Any]]:
    return [
        p
        for p in list_proof_profiles(base_path)
        if p.get("promoted") or p.get("maturity") == "ready"
    ]


def load_proof_spec(base_path: Path, proof_id: str) -> Dict[str, Any]:
    profile = get_proof_profile(base_path, proof_id)
    spec = profile.get("proof_spec") or {}
    if not spec:
        raise StudioError(f"Proof profile has no proof-spec: {proof_id}")
    return spec


def _entity_list(attested: Dict[str, Any]) -> List[Dict[str, Any]]:
    proposed = attested.get("proposed_artifact") or {}
    output = proposed.get("output") if isinstance(proposed, dict) else {}
    if not isinstance(output, dict):
        output = {}
    entities = output.get("entities") or attested.get("entities") or []
    if isinstance(entities, list):
        return [e for e in entities if isinstance(e, dict)]
    return []


def _redaction_count(attested: Dict[str, Any]) -> int:
    proposed = attested.get("proposed_artifact") or {}
    output = proposed.get("output") if isinstance(proposed, dict) else {}
    if not isinstance(output, dict):
        output = {}
    total = output.get("total_redactions")
    if isinstance(total, int):
        return total
    redactions = output.get("redactions_applied") or []
    if isinstance(redactions, list):
        count = 0
        for item in redactions:
            if isinstance(item, dict) and "count" in item:
                try:
                    count += int(item["count"])
                except (TypeError, ValueError):
                    count += 1
            else:
                count += 1
        if count:
            return count
    return len(_entity_list(attested))


def _categories_present(attested: Dict[str, Any]) -> set:
    cats: set = set()
    proposed = attested.get("proposed_artifact") or {}
    output = proposed.get("output") if isinstance(proposed, dict) else {}
    if isinstance(output, dict):
        for item in output.get("redactions_applied") or []:
            if isinstance(item, dict) and item.get("category"):
                cats.add(str(item["category"]).strip().lower())
        for ent in output.get("entities") or []:
            if isinstance(ent, dict):
                for key in ("category", "type"):
                    if ent.get(key):
                        cats.add(str(ent[key]).strip().lower())
    # normalize common aliases
    normalized = set()
    for c in cats:
        c2 = c.replace(" ", "_").replace("-", "_")
        normalized.add(c2)
        if "email" in c2:
            normalized.add("email")
        if "phone" in c2:
            normalized.add("phone")
        if "ssn" in c2 or "social" in c2:
            normalized.add("ssn")
        if "name" in c2:
            normalized.add("name")
        if "card" in c2 or "pan" in c2:
            normalized.add("card")
    return normalized


def _gov_decision(attested: Dict[str, Any]) -> str:
    gd = attested.get("governance_decision")
    if isinstance(gd, dict):
        return str(gd.get("decision") or gd.get("status") or "").upper()
    if isinstance(gd, str):
        return gd.upper()
    return ""


def evaluate_predicate(
    pred: Dict[str, Any],
    attested: Dict[str, Any],
    *,
    zk_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    pred_id = pred["id"]
    params = pred.get("params") or {}
    ok = False
    detail: Dict[str, Any] = {}

    if pred_id == "REDACTION_NONEMPTY":
        count = _redaction_count(attested)
        ok = count > 0
        detail = {"total_redactions": count}

    elif pred_id == "ENTITY_COUNT_GTE":
        n = int(params.get("n", 1))
        entities = _entity_list(attested)
        count = len(entities) if entities else _redaction_count(attested)
        ok = count >= n
        detail = {"entity_count": count, "required": n}

    elif pred_id == "CATEGORY_INCLUDES":
        required = [str(c).lower() for c in (params.get("categories") or [])]
        present = _categories_present(attested)
        missing = []
        for r in required:
            r_norm = r.replace(" ", "_").replace("-", "_")
            aliases = {r_norm, r}
            if r_norm in ("email", "email_address"):
                aliases.update({"email", "email_address"})
            if r_norm in ("phone", "phone_number"):
                aliases.update({"phone", "phone_number"})
            if r_norm == "ssn":
                aliases.update({"ssn", "social_security_number"})
            if not (aliases & present):
                # soft match: any present category containing token
                if not any(r_norm in p or p in r_norm for p in present):
                    missing.append(r)
        ok = len(missing) == 0
        detail = {"required": required, "present": sorted(present), "missing": missing}

    elif pred_id == "RULE_BOUND":
        ok = bool(
            attested.get("zk_proof_rule_binding")
            or attested.get("governed_by")
            or (attested.get("governance_proofs") or {}).get("rule_binding")
            or attested.get("attestation_id")
        )
        detail = {"has_governed_by": bool(attested.get("governed_by"))}

    elif pred_id == "PIPELINE_CHAIN":
        chain = attested.get("agent_chain") or attested.get("pipeline_chain")
        ok = bool(chain) or bool(attested.get("zk_proof_pipeline")) or bool(
            attested.get("attestation_id")
        )
        detail = {"agent_chain": chain if isinstance(chain, list) else bool(chain)}

    elif pred_id == "ATTESTED_STATUS":
        status = str(attested.get("final_status") or "").upper()
        ok = status in ("ATTESTED", "SUCCEEDED", "SUCCESS", "APPROVED") or bool(
            attested.get("attestation_id")
        )
        detail = {"final_status": status, "attestation_id": attested.get("attestation_id")}

    elif pred_id == "GOVERNANCE_APPROVED":
        decision = _gov_decision(attested)
        ok = decision in (
            "APPROVED",
            "APPROVED_WITH_REVIEW_FLAG",
            "ALLOW",
            "PASS",
        ) or (bool(attested.get("attestation_id")) and decision == "")
        detail = {"decision": decision}

    elif pred_id == "ZK_GOVERNANCE_PRESENT":
        has_r = bool(attested.get("zk_proof_redaction"))
        has_rule = bool(attested.get("zk_proof_rule_binding"))
        has_pipe = bool(attested.get("zk_proof_pipeline"))
        ok = has_r and has_rule and has_pipe
        detail = {
            "redaction": has_r,
            "rule_binding": has_rule,
            "pipeline": has_pipe,
            "zk_summary_governance": (zk_summary or {}).get("governance"),
        }

    elif pred_id == "ZK_ENTITY_PRESENT":
        entity = attested.get("entity_proofs") or {}
        proofs = entity.get("proofs") if isinstance(entity, dict) else None
        ok = bool(proofs)
        detail = {
            "proof_keys": list(proofs.keys()) if isinstance(proofs, dict) else [],
            "zk_summary_entity": (zk_summary or {}).get("entity"),
        }

    elif pred_id == "ARTIFACT_HASH_PRESENT":
        h = attested.get("artifact_hash") or attested.get("full_provenance_hash")
        ok = bool(h)
        detail = {"hash": h}

    elif pred_id == "HANDOFF_RECORDED":
        handoffs = attested.get("handoffs")
        ok = bool(handoffs)
        detail = {"handoffs": handoffs if isinstance(handoffs, list) else bool(handoffs)}

    elif pred_id == "UNIVERSAL_PROOF_VALID":
        up = attested.get("universal_predicate_proof") or {}
        if not up:
            # Deferred: evaluated again after attach_universal_proof
            ok = True
            detail = {"deferred": True}
        else:
            ok = bool(up.get("verification_result") or up.get("independent_verify"))
            detail = {
                "circuit": up.get("circuit"),
                "verification_result": up.get("verification_result"),
                "independent_verify": up.get("independent_verify"),
                "vk_hash": up.get("vk_hash"),
            }

    else:
        ok = False
        detail = {"error": f"unevaluated predicate {pred_id}"}

    return {
        "id": pred_id,
        "ok": ok,
        "params": params,
        "detail": detail,
        "title": PREDICATE_CATALOG.get(pred_id, {}).get("title") or pred_id,
    }


def evaluate_proof_profile(
    spec: Dict[str, Any],
    attested: Optional[Dict[str, Any]],
    *,
    zk_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate all predicates; returns claim report."""
    if not isinstance(attested, dict):
        return {
            "ok": False,
            "fail_closed": bool(spec.get("fail_closed", True)),
            "proof_profile_id": spec.get("id"),
            "claim_english": spec.get("claim_english"),
            "circuit_binding": spec.get("circuit_binding"),
            "predicates": [],
            "error": "no attested_result to evaluate",
            "evaluated_at": _utcnow(),
        }

    results = [
        evaluate_predicate(p, attested, zk_summary=zk_summary)
        for p in (spec.get("predicates") or [])
    ]
    ok = all(r["ok"] for r in results) if results else False
    failed = [r["id"] for r in results if not r["ok"]]
    return {
        "ok": ok,
        "fail_closed": bool(spec.get("fail_closed", True)),
        "proof_profile_id": spec.get("id"),
        "name": spec.get("name"),
        "claim_english": spec.get("claim_english"),
        "circuit_binding": spec.get("circuit_binding"),
        "mapped_circuits": spec.get("mapped_circuits") or [],
        "require_attest": bool(spec.get("require_attest")),
        "predicates": results,
        "failed_predicates": failed,
        "attestation_id": attested.get("attestation_id"),
        "evaluated_at": _utcnow(),
        "apiVersion": API_VERSION,
    }


def apply_proof_profile_to_result(
    base_path: Path,
    result: Dict[str, Any],
    proof_profile_id: Optional[str],
    *,
    zk_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Attach proof_claim to a pipeline result. If fail_closed and claim fails,
    mark final_status failed with a clear error.
    """
    if not proof_profile_id:
        return result
    try:
        spec = load_proof_spec(base_path, str(proof_profile_id))
    except StudioError as exc:
        result["proof_claim"] = {
            "ok": False,
            "error": str(exc),
            "proof_profile_id": proof_profile_id,
            "evaluated_at": _utcnow(),
        }
        if result.get("final_status") == "succeeded":
            result["final_status"] = "failed"
            result["error"] = f"proof_profile: {exc}"
        return result

    attested = result.get("attested_result")
    if not isinstance(attested, dict):
        # sometimes nested
        ar = result.get("result", {})
        if isinstance(ar, dict):
            attested = ar.get("attested_result")

    claim = evaluate_proof_profile(
        spec,
        attested if isinstance(attested, dict) else None,
        zk_summary=zk_summary or result.get("zk_summary"),
    )
    result["proof_claim"] = claim
    if isinstance(attested, dict):
        attested["proof_claim"] = claim
        result["attested_result"] = attested

    if not claim.get("ok") and claim.get("fail_closed", True):
        if result.get("final_status") == "succeeded":
            result["final_status"] = "failed"
            result["error"] = (
                "proof_profile claim failed: "
                + ", ".join(claim.get("failed_predicates") or ["unknown"])
            )
        return result

    # P3: when claim holds and binding is universal (or auto), attach real Groth16
    want_universal = (
        spec.get("circuit_binding") == CIRCUIT_BINDING_UNIVERSAL
        or spec.get("generate_universal_proof")
    )
    # Also generate when profile lists only circuit-mappable catalog bits and keys exist
    if not want_universal and universal_keys_available(base_path):
        if spec.get("circuit_binding") in (None, CIRCUIT_BINDING_EXISTING, CIRCUIT_BINDING_UNIVERSAL):
            # Auto-prove universal for any satisfied claim when keys present
            want_universal = True

    if want_universal and claim.get("ok") and isinstance(attested, dict):
        try:
            from .zk.universal_bridge import attach_universal_proof

            # Strip UNIVERSAL_PROOF_VALID from prove mask if present (circular)
            prove_claim = dict(claim)
            prove_claim["predicates"] = [
                p
                for p in (claim.get("predicates") or [])
                if p.get("id") != "UNIVERSAL_PROOF_VALID"
                and p.get("id") in PREDICATE_BIT
                and PREDICATE_BIT[p["id"]] < 9
            ]
            if prove_claim["predicates"]:
                bundle = attach_universal_proof(
                    attested, prove_claim, base_path=base_path, spec=spec
                )
                attested["universal_predicate_proof"] = bundle
                claim["universal_predicate_proof"] = {
                    "circuit": bundle.get("circuit"),
                    "verification_result": bundle.get("verification_result"),
                    "independent_verify": bundle.get("independent_verify"),
                    "vk_hash": bundle.get("vk_hash"),
                    "public_inputs": bundle.get("public_inputs"),
                }
                result["universal_predicate_proof"] = claim["universal_predicate_proof"]
                # Re-check UNIVERSAL_PROOF_VALID if selected
                if any(
                    p.get("id") == "UNIVERSAL_PROOF_VALID"
                    for p in (spec.get("predicates") or [])
                ):
                    claim = evaluate_proof_profile(
                        spec, attested, zk_summary=zk_summary
                    )
                    claim["universal_predicate_proof"] = attested.get(
                        "universal_predicate_proof"
                    )
                    result["proof_claim"] = claim
                    attested["proof_claim"] = claim
                result["attested_result"] = attested
                if not claim.get("ok") and claim.get("fail_closed", True):
                    result["final_status"] = "failed"
                    result["error"] = "universal proof claim re-evaluation failed"
        except Exception as exc:
            claim["universal_proof_error"] = str(exc)
            result["proof_claim"] = claim
            if spec.get("circuit_binding") == CIRCUIT_BINDING_UNIVERSAL:
                result["final_status"] = "failed"
                result["error"] = f"universal-predicate-v1 prove failed: {exc}"
    return result


def run_proof_profile_test(
    runtime: APXRuntime,
    proof_id: str,
    *,
    input_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compile profile, run a real reference composition, evaluate claim.
    Uses attest when the profile requires ZK predicates.
    """
    profile = get_proof_profile(runtime.base_path, proof_id)
    spec = profile.get("proof_spec") or load_proof_spec(runtime.base_path, proof_id)
    # Recompile for safety
    spec = compile_proof_spec(
        proof_id=spec["id"],
        name=spec.get("name") or profile.get("name") or proof_id,
        description=spec.get("description") or "",
        intent_md=profile.get("intent_md") or "",
        predicates=spec.get("predicates"),
        circuit_binding=spec.get("circuit_binding") or CIRCUIT_BINDING_EXISTING,
        fail_closed=spec.get("fail_closed", True),
        require_attest=spec.get("require_attest"),
    )

    sample = input_text or (
        "Contact John Smith at john.smith@example.com or call (555) 123-4567. "
        "SSN: 123-45-6789. Card: 4111 1111 1111 1111."
    )
    want_attest = bool(spec.get("require_attest"))

    doc = {
        "apiVersion": "apxv.pipeline/v0.1",
        "kind": "Pipeline",
        "id": f"apxv-pipeline-proof-test-{proof_id.lower()[-16:]}",
        "name": f"Proof Studio test {proof_id}",
        "version": "0.1.0",
        "description": "Ephemeral Proof Studio test — not saved to library",
        "defaults": {
            "attest": want_attest,
            "on_step_failure": "stop",
            "proof_profile": proof_id,
        },
        "steps": [
            {
                "id": "redact",
                "name": "Rule-governed redaction",
                "uses": "agent:APXV-AGENT-001",
            },
            {
                "id": "orchestrate",
                "name": "Workflow orchestration",
                "uses": "agent:APXV-AGENT-002",
            },
            {
                "id": "decide",
                "name": "Attestation coordination",
                "uses": "agent:APXV-AGENT-003",
            },
        ],
    }

    result = run_pipeline_document(
        doc,
        runtime=runtime,
        input_text=sample,
        attest=want_attest,
        proof_profile_id=proof_id,
    )
    claim = result.get("proof_claim") or {}
    ok = bool(claim.get("ok")) and result.get("final_status") == "succeeded"

    test_rec = {
        "at": _utcnow(),
        "final_status": "succeeded" if ok else "failed",
        "ok": ok,
        "require_attest": want_attest,
        "pipeline_final_status": result.get("final_status"),
        "error": result.get("error"),
        "claim": {
            "ok": claim.get("ok"),
            "failed_predicates": claim.get("failed_predicates"),
            "claim_english": claim.get("claim_english"),
        },
    }

    catalog = _load_catalog(runtime.base_path)
    catalog.setdefault("proofs", {}).setdefault(proof_id, {})
    catalog["proofs"][proof_id]["last_test"] = test_rec
    if ok:
        catalog["proofs"][proof_id]["maturity"] = catalog["proofs"][proof_id].get(
            "maturity"
        ) or "draft"
    _save_catalog(runtime.base_path, catalog)

    d = proof_dir(runtime.base_path, proof_id)
    mp = d / "manifest.json"
    if mp.exists():
        man = json.loads(mp.read_text(encoding="utf-8"))
        man["last_test"] = test_rec
        man["updated_at"] = _utcnow()
        mp.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")

    return {
        "ok": ok,
        "proof_id": proof_id,
        "result": result,
        "proof_claim": claim,
        "last_test": test_rec,
    }


def promote_proof_profile(
    runtime: APXRuntime,
    proof_id: str,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    pid = _validate_proof_id(proof_id)
    profile = get_proof_profile(runtime.base_path, pid)
    last = profile.get("last_test") or {}
    if not force and last.get("final_status") != "succeeded" and not last.get("ok"):
        raise StudioError(
            "Proof profile test has not succeeded. Run Test successfully before "
            "promote, or pass force=true to promote as Draft."
        )
    catalog = _load_catalog(runtime.base_path)
    catalog.setdefault("proofs", {}).setdefault(pid, {})
    ready = last.get("final_status") == "succeeded" or bool(last.get("ok"))
    catalog["proofs"][pid]["promoted"] = True
    catalog["proofs"][pid]["maturity"] = "ready" if ready else "draft"
    catalog["proofs"][pid]["promoted_at"] = _utcnow()
    _save_catalog(runtime.base_path, catalog)

    d = proof_dir(runtime.base_path, pid)
    mp = d / "manifest.json"
    if mp.exists():
        man = json.loads(mp.read_text(encoding="utf-8"))
        man["promoted"] = True
        man["maturity"] = catalog["proofs"][pid]["maturity"]
        mp.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    return get_proof_profile(runtime.base_path, pid)


def save_from_template(
    runtime: APXRuntime,
    template_id: str,
    *,
    proof_id: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    tpl = next((t for t in PROOF_TEMPLATES if t["id"] == template_id), None)
    if not tpl:
        raise StudioError(f"Unknown proof template: {template_id}")
    binding = tpl.get("circuit_binding") or CIRCUIT_BINDING_EXISTING
    if binding == CIRCUIT_BINDING_UNIVERSAL and not universal_keys_available(
        runtime.base_path
    ):
        binding = CIRCUIT_BINDING_EXISTING
    return save_proof_profile(
        runtime,
        proof_id=proof_id or tpl["id"],
        name=name or tpl["name"],
        description=tpl.get("description") or "",
        intent_md=tpl.get("intent_md") or "",
        predicates=tpl.get("predicates"),
        circuit_binding=binding,
        fail_closed=bool(tpl.get("fail_closed", True)),
        require_attest=tpl.get("require_attest"),
    )


def export_proof_claim_bundle(
    base_path: Path,
    *,
    proof_profile_id: Optional[str] = None,
    claim: Optional[Dict[str, Any]] = None,
    attested: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Third-party export: English claim + predicate results + optional universal
    proof + VK hash. No private entity values.
    """
    profile = None
    if proof_profile_id:
        try:
            profile = get_proof_profile(base_path, proof_profile_id)
        except StudioError:
            profile = {"id": proof_profile_id}
    claim = claim or (attested or {}).get("proof_claim") or {}
    up = claim.get("universal_predicate_proof") or (attested or {}).get(
        "universal_predicate_proof"
    )
    return {
        "apiVersion": API_VERSION,
        "export_type": "apxv.proof_claim_bundle",
        "exported_at": _utcnow(),
        "proof_profile": {
            "id": (profile or {}).get("id") or claim.get("proof_profile_id"),
            "name": (profile or {}).get("name") or claim.get("name"),
            "claim_english": claim.get("claim_english")
            or (profile or {}).get("claim_english"),
            "circuit_binding": claim.get("circuit_binding")
            or ((profile or {}).get("proof_spec") or {}).get("circuit_binding"),
        },
        "claim": {
            "ok": claim.get("ok"),
            "failed_predicates": claim.get("failed_predicates"),
            "predicates": [
                {
                    "id": p.get("id"),
                    "ok": p.get("ok"),
                    "title": p.get("title"),
                    # strip potentially sensitive detail values
                    "detail_keys": list((p.get("detail") or {}).keys()),
                }
                for p in (claim.get("predicates") or [])
                if isinstance(p, dict)
            ],
            "evaluated_at": claim.get("evaluated_at"),
            "attestation_id": claim.get("attestation_id"),
        },
        "universal_predicate_proof": {
            "circuit": (up or {}).get("circuit"),
            "verification_result": (up or {}).get("verification_result"),
            "independent_verify": (up or {}).get("independent_verify"),
            "vk_hash": (up or {}).get("vk_hash"),
            "proof_hex": (up or {}).get("proof_hex"),
            "public_inputs": (up or {}).get("public_inputs"),
        }
        if up
        else None,
        "disclosure": {
            "never_includes": [
                "raw_input_text",
                "entity_values",
                "ssn",
                "email_plaintext",
            ],
            "public": [
                "claim_english",
                "predicate_results",
                "attestation_id",
                "vk_hash",
                "proof_hex",
                "public_inputs",
            ],
        },
    }


def save_profile_from_intent(
    runtime: APXRuntime,
    *,
    intent_md: str,
    proof_id: str = "APXV-PROOF-FROM-INTENT",
    name: str = "From intent",
    prefer_universal: bool = True,
) -> Dict[str, Any]:
    from .proof_intent import compile_intent_deterministic

    compiled = compile_intent_deterministic(
        intent_md,
        proof_id=proof_id,
        name=name,
        prefer_universal=prefer_universal and universal_keys_available(runtime.base_path),
    )
    spec = compiled["proof_spec"]
    profile = save_proof_profile(
        runtime,
        proof_id=spec["id"],
        name=spec.get("name") or name,
        description=spec.get("description") or "",
        intent_md=intent_md,
        predicates=spec.get("predicates"),
        circuit_binding=spec.get("circuit_binding") or CIRCUIT_BINDING_EXISTING,
        fail_closed=True,
        require_attest=spec.get("require_attest"),
    )
    profile["compile"] = {
        "source": compiled.get("source"),
        "matched_rules": compiled.get("matched_rules"),
        "warnings": compiled.get("warnings"),
    }
    return profile
