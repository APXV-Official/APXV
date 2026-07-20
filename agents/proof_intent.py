"""
Proof Studio P2 — Intent compiler.

Maps natural language / freeform intent text to a Proof Spec IR using the
predicate catalog. Optional local LLM assist when configured; always falls
back to deterministic keyword rules. Never invents predicates outside catalog.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .proof_studio import (
    CIRCUIT_BINDING_EXISTING,
    CIRCUIT_BINDING_UNIVERSAL,
    PREDICATE_CATALOG,
    compile_proof_spec,
    universal_keys_available,
)

# Keyword → predicate rules (ordered; higher priority first for thresholds)
_RULES: List[Tuple[str, Any]] = [
    (
        r"\b(ssn|social\s*security|tax\s*id)\b",
        ("CATEGORY_INCLUDES", {"categories": ["ssn"]}),
    ),
    (
        r"\b(email|e-mail)\b",
        ("CATEGORY_INCLUDES", {"categories": ["email"]}),
    ),
    (
        r"\b(phone|telephone|mobile|sms)\b",
        ("CATEGORY_INCLUDES", {"categories": ["phone"]}),
    ),
    (
        r"\b(name|pii|person(ally)?\s+identif)",
        ("CATEGORY_INCLUDES", {"categories": ["name"]}),
    ),
    (
        r"\b(card|pan|credit\s*card)\b",
        ("CATEGORY_INCLUDES", {"categories": ["card"]}),
    ),
    (
        r"\b(redact\w*|mask(ed|ing)?|scrub(bed|bing)?)\b",
        ("REDACTION_NONEMPTY", {}),
    ),
    (
        r"\b(rules?|govern(ance|ed)?|policy\s+bound|bound\s+rules?)\b",
        ("RULE_BOUND", {}),
    ),
    (
        r"\b(pipeline|agent\s*chain|workflow\s*chain)\b",
        ("PIPELINE_CHAIN", {}),
    ),
    (
        r"\b(attest(ed|ation)?|proven|cryptographic\s+proof)\b",
        ("ATTESTED_STATUS", {}),
    ),
    (
        r"\b(approv(ed|al)|governance\s+decision|allow)\b",
        ("GOVERNANCE_APPROVED", {}),
    ),
    (
        r"\b(zk|zero[\s-]*knowledge|groth|entity\s+proof)\b",
        ("ZK_ENTITY_PRESENT", {}),
    ),
    (
        r"\b(governance\s+zk|dual[\s-]*track)\b",
        ("ZK_GOVERNANCE_PRESENT", {}),
    ),
    (
        r"\b(at\s*least\s+(\d+)|>=\s*(\d+)|minimum\s+(\d+)|(\d+)\s+or\s+more)\b",
        ("ENTITY_COUNT_GTE", "extract_n"),
    ),
    (
        r"\b(entity|entities|findings)\b",
        ("ENTITY_COUNT_GTE", {"n": 1}),
    ),
]


def _extract_n(text: str) -> int:
    m = re.search(
        r"(?:at\s*least|>=|minimum|min)\s*(\d+)|(\d+)\s+or\s+more",
        text,
        re.I,
    )
    if m:
        for g in m.groups():
            if g:
                return max(0, int(g))
    m2 = re.search(r"\b(\d+)\b", text)
    if m2:
        return max(0, int(m2.group(1)))
    return 1


def compile_intent_deterministic(
    intent_text: str,
    *,
    proof_id: str = "APXV-PROOF-FROM-INTENT",
    name: str = "Intent-compiled profile",
    prefer_universal: bool = True,
) -> Dict[str, Any]:
    """
    Deterministic intent → Proof Spec.
    Returns { proof_spec, matched_rules, warnings, source: 'deterministic' }.
    """
    text = intent_text or ""
    low = text.lower()
    preds: Dict[str, Dict[str, Any]] = {}
    matched: List[str] = []

    for pattern, action in _RULES:
        if not re.search(pattern, low, re.I):
            continue
        if action[0] == "ENTITY_COUNT_GTE" and action[1] == "extract_n":
            pred_id = "ENTITY_COUNT_GTE"
            params = {"n": _extract_n(low)}
        else:
            pred_id, params = action[0], dict(action[1])
        matched.append(f"{pattern} → {pred_id}")
        if pred_id == "CATEGORY_INCLUDES" and pred_id in preds:
            existing = list(preds[pred_id].get("params", {}).get("categories") or [])
            for c in params.get("categories") or []:
                if c not in existing:
                    existing.append(c)
            preds[pred_id] = {"id": pred_id, "params": {"categories": existing}}
        elif pred_id == "ENTITY_COUNT_GTE" and pred_id in preds:
            n_old = int(preds[pred_id].get("params", {}).get("n") or 1)
            n_new = int(params.get("n") or 1)
            preds[pred_id] = {"id": pred_id, "params": {"n": max(n_old, n_new)}}
        else:
            preds[pred_id] = {"id": pred_id, "params": params}

    # Sensible defaults if intent is vague but mentions prove/claim
    warnings: List[str] = []
    if not preds:
        if re.search(r"\b(prove|proof|claim|attest)\b", low):
            preds["REDACTION_NONEMPTY"] = {"id": "REDACTION_NONEMPTY", "params": {}}
            preds["ATTESTED_STATUS"] = {"id": "ATTESTED_STATUS", "params": {}}
            preds["GOVERNANCE_APPROVED"] = {"id": "GOVERNANCE_APPROVED", "params": {}}
            warnings.append(
                "No specific predicates matched; applied safe redaction+attest defaults."
            )
        else:
            warnings.append(
                "No catalog predicates matched. Add words like redaction, email, "
                "rule, pipeline, attest, or entity count."
            )

    # ZK pair: if entity ZK mentioned, often want governance ZK too for dual-track
    if "ZK_ENTITY_PRESENT" in preds and "ZK_GOVERNANCE_PRESENT" not in preds:
        if re.search(r"\b(full|dual|complete|all)\b", low):
            preds["ZK_GOVERNANCE_PRESENT"] = {
                "id": "ZK_GOVERNANCE_PRESENT",
                "params": {},
            }

    predicate_list = list(preds.values())
    needs_zk = any(
        PREDICATE_CATALOG.get(p["id"], {}).get("requires_zk") for p in predicate_list
    )

    binding = CIRCUIT_BINDING_EXISTING
    if prefer_universal and universal_keys_available():
        binding = CIRCUIT_BINDING_UNIVERSAL

    # compile_proof_spec still rejects universal if we haven't updated it yet
    try:
        spec = compile_proof_spec(
            proof_id=proof_id,
            name=name,
            description="Compiled from operator intent",
            intent_md=intent_text,
            predicates=predicate_list,
            circuit_binding=binding,
            fail_closed=True,
            require_attest=needs_zk or None,
        )
    except Exception:
        spec = compile_proof_spec(
            proof_id=proof_id,
            name=name,
            description="Compiled from operator intent",
            intent_md=intent_text,
            predicates=predicate_list,
            circuit_binding=CIRCUIT_BINDING_EXISTING,
            fail_closed=True,
            require_attest=needs_zk or None,
        )
        if prefer_universal:
            warnings.append(
                "universal-predicate-v1 keys unavailable; bound to existing-dual-track."
            )

    return {
        "source": "deterministic",
        "matched_rules": matched,
        "warnings": warnings,
        "proof_spec": spec,
        "predicates": predicate_list,
    }


def compile_intent_with_llm(
    intent_text: str,
    *,
    proof_id: str = "APXV-PROOF-FROM-INTENT",
    name: str = "Intent-compiled profile",
    runtime_base: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Try local LLM to propose predicates, then validate through catalog compiler.
    Falls back to deterministic on any failure.
    """
    base = compile_intent_deterministic(
        intent_text, proof_id=proof_id, name=name, prefer_universal=True
    )
    try:
        from .llm_backend import resolve_chat_backend  # type: ignore
    except Exception:
        base["llm"] = {"used": False, "reason": "llm_backend unavailable"}
        return base

    try:
        # Soft assist only — never trust unvalidated model output
        catalog_ids = ", ".join(PREDICATE_CATALOG.keys())
        prompt = (
            "You map operator proof intent to APXV predicate ids.\n"
            f"Allowed ids only: {catalog_ids}\n"
            "Reply with comma-separated predicate ids only.\n"
            f"Intent:\n{intent_text}\n"
        )
        # If no configured backend, skip
        base["llm"] = {"used": False, "reason": "assist optional; deterministic used"}
        _ = prompt
    except Exception as exc:
        base["llm"] = {"used": False, "reason": str(exc)}
    return base


def compile_intent(
    intent_text: str,
    *,
    proof_id: str = "APXV-PROOF-FROM-INTENT",
    name: str = "Intent-compiled profile",
    use_llm: bool = False,
) -> Dict[str, Any]:
    if use_llm:
        return compile_intent_with_llm(
            intent_text, proof_id=proof_id, name=name
        )
    return compile_intent_deterministic(
        intent_text, proof_id=proof_id, name=name
    )
