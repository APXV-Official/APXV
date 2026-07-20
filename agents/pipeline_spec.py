"""
APXV Pipeline Spec v0.1 — validate, load, dump (YAML + JSON round-trip).

Contract: Workshop specs/PIPELINE-SPEC-v0.1.md
APXV language only. Stdlib-first; no third-party product naming.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

API_VERSION = "apxv.pipeline/v0.1"
KIND = "Pipeline"
MAX_STEPS = 32

ID_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9._-]*$")
PIPELINE_ID_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9._-]*$")
USES_AGENT_RE = re.compile(r"^agent:(?P<id>[A-Za-z0-9._-]+)$")
USES_PACK_RE = re.compile(r"^pack:(?P<id>apxv-pack-[a-z0-9][a-z0-9-]*)$")
USES_ATTEST = "apxv:attest"
USES_APPROVE = "apxv:approve"
USES_HANDOFF = "apxv:handoff"
USES_LOOP = "apxv:loop"
# Accept v0.1 and additive v0.1.x documents
API_VERSIONS = frozenset({API_VERSION, "apxv.pipeline/v0.1.1"})

SECRET_KEY_HINTS = (
    "password",
    "secret",
    "api_key",
    "apikey",
    "private_key",
    "token",
    "credential",
)


class PipelineSpecError(ValueError):
    """Invalid pipeline document or binding."""


@dataclass
class ValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    document: Optional[Dict[str, Any]] = None

    def raise_if_invalid(self) -> Dict[str, Any]:
        if not self.ok or self.document is None:
            raise PipelineSpecError("; ".join(self.errors) or "invalid pipeline")
        return self.document


def parse_uses(uses: str) -> Dict[str, str]:
    raw = (uses or "").strip()
    if raw == USES_ATTEST:
        return {"kind": "attest"}
    if raw == USES_APPROVE:
        return {"kind": "approve"}
    if raw == USES_HANDOFF:
        return {"kind": "handoff"}
    if raw == USES_LOOP:
        return {"kind": "loop"}
    m = USES_AGENT_RE.match(raw)
    if m:
        return {"kind": "agent", "agent_id": m.group("id")}
    m = USES_PACK_RE.match(raw)
    if m:
        return {"kind": "pack", "pack_id": m.group("id")}
    raise PipelineSpecError(
        f"unknown uses binding {uses!r}; expected agent:<ID>, pack:apxv-pack-<slug>, "
        "apxv:attest, apxv:approve, apxv:handoff, or apxv:loop"
    )


def _check_secret_keys(obj: Any, path: str, errors: List[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_l = str(key).lower().replace("-", "_")
            full = f"{path}.{key}" if path else str(key)
            if any(hint in key_l for hint in SECRET_KEY_HINTS):
                errors.append(f"config must not include secret-like key {full!r}")
            _check_secret_keys(value, full, errors)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _check_secret_keys(item, f"{path}[{i}]", errors)


def _known_top_level() -> set:
    return {
        "apiVersion",
        "kind",
        "id",
        "name",
        "version",
        "steps",
        "edges",
        "description",
        "metadata",
        "defaults",
        "requires_apxv",
    }


EDGE_KINDS = frozenset({"success", "failure", "always"})


def _known_step_keys() -> set:
    return {
        "id",
        "name",
        "uses",
        "description",
        "config",
        "capabilities_required",
        "on_failure",
        "timeout_seconds",
        "pack_profile",
        "when",
        "next_on_success",
        "next_on_failure",
        "layout",
        "enabled",
    }


def validate_pipeline_document(raw: Any) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(raw, dict):
        return ValidationResult(ok=False, errors=["pipeline document must be an object"])

    for key in raw:
        if key not in _known_top_level():
            warnings.append(f"unknown top-level field {key!r} (forward-compatible warning)")

    api_version = raw.get("apiVersion")
    if api_version not in API_VERSIONS:
        errors.append(
            f"apiVersion must be one of {sorted(API_VERSIONS)!r}, got {api_version!r}"
        )

    kind = raw.get("kind")
    if kind != KIND:
        errors.append(f"kind must be {KIND!r}, got {kind!r}")

    pipeline_id = raw.get("id")
    if not isinstance(pipeline_id, str) or not pipeline_id.strip():
        errors.append("id is required")
    elif not PIPELINE_ID_RE.match(pipeline_id):
        errors.append(f"id {pipeline_id!r} is invalid")

    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("name is required")

    version = raw.get("version")
    if not isinstance(version, str) or not version.strip():
        errors.append("version is required")

    steps = raw.get("steps")
    if not isinstance(steps, list) or len(steps) < 1:
        errors.append("steps must be a non-empty array")
    elif len(steps) > MAX_STEPS:
        errors.append(f"steps exceed soft limit of {MAX_STEPS}")

    step_ids: List[str] = []
    if isinstance(steps, list):
        for index, step in enumerate(steps):
            prefix = f"steps[{index}]"
            if not isinstance(step, dict):
                errors.append(f"{prefix} must be an object")
                continue
            for key in step:
                if key not in _known_step_keys():
                    warnings.append(f"unknown step field {prefix}.{key}")
            sid = step.get("id")
            if not isinstance(sid, str) or not sid.strip():
                errors.append(f"{prefix}.id is required")
            elif not ID_RE.match(sid):
                errors.append(f"{prefix}.id {sid!r} is invalid")
            else:
                if sid in step_ids:
                    errors.append(f"duplicate step id {sid!r}")
                step_ids.append(sid)
            if not isinstance(step.get("name"), str) or not str(step.get("name")).strip():
                errors.append(f"{prefix}.name is required")
            uses = step.get("uses")
            if not isinstance(uses, str) or not uses.strip():
                errors.append(f"{prefix}.uses is required")
            else:
                try:
                    parse_uses(uses)
                except PipelineSpecError as exc:
                    errors.append(f"{prefix}.uses: {exc}")
            on_failure = step.get("on_failure")
            if on_failure is not None and on_failure not in ("stop", "continue"):
                errors.append(f"{prefix}.on_failure must be 'stop' or 'continue'")
            caps = step.get("capabilities_required")
            if caps is not None:
                if not isinstance(caps, list) or not all(isinstance(c, str) for c in caps):
                    errors.append(f"{prefix}.capabilities_required must be a string array")
            config = step.get("config")
            if config is not None:
                if not isinstance(config, dict):
                    errors.append(f"{prefix}.config must be an object")
                else:
                    _check_secret_keys(config, f"{prefix}.config", errors)
            timeout = step.get("timeout_seconds")
            if timeout is not None and not isinstance(timeout, (int, float)):
                errors.append(f"{prefix}.timeout_seconds must be a number")
            pack_profile = step.get("pack_profile")
            if pack_profile is not None:
                if not isinstance(pack_profile, str) or not str(pack_profile).startswith(
                    "apxv-pack-"
                ):
                    errors.append(
                        f"{prefix}.pack_profile must be an apxv-pack-* id when set"
                    )
            when = step.get("when")
            if when is not None and when not in (
                "always",
                "previous_succeeded",
                "previous_failed",
            ):
                errors.append(
                    f"{prefix}.when must be always|previous_succeeded|previous_failed"
                )
            for jump_key in ("next_on_success", "next_on_failure"):
                jump = step.get(jump_key)
                if jump is not None and not isinstance(jump, str):
                    errors.append(f"{prefix}.{jump_key} must be a step id string")
            layout = step.get("layout")
            if layout is not None and not isinstance(layout, dict):
                errors.append(f"{prefix}.layout must be an object when set")

    if isinstance(steps, list) and step_ids:
        id_set = set(step_ids)
        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            for jump_key in ("next_on_success", "next_on_failure"):
                jump = step.get(jump_key)
                if isinstance(jump, str) and jump and jump not in id_set:
                    errors.append(
                        f"steps[{index}].{jump_key} target {jump!r} is not a step id"
                    )

    edges = raw.get("edges")
    if edges is not None:
        if not isinstance(edges, list):
            errors.append("edges must be an array when set")
        else:
            id_set = set(step_ids) if step_ids else set()
            for index, edge in enumerate(edges):
                prefix = f"edges[{index}]"
                if not isinstance(edge, dict):
                    errors.append(f"{prefix} must be an object")
                    continue
                for key in edge:
                    if key not in ("id", "from", "to", "kind"):
                        warnings.append(f"unknown edge field {prefix}.{key}")
                src = edge.get("from")
                dst = edge.get("to")
                kind = edge.get("kind") or "success"
                if not isinstance(src, str) or not src.strip():
                    errors.append(f"{prefix}.from is required")
                elif id_set and src not in id_set:
                    errors.append(f"{prefix}.from {src!r} is not a step id")
                if not isinstance(dst, str) or not dst.strip():
                    errors.append(f"{prefix}.to is required")
                elif id_set and dst not in id_set:
                    errors.append(f"{prefix}.to {dst!r} is not a step id")
                if kind not in EDGE_KINDS:
                    errors.append(
                        f"{prefix}.kind must be success|failure|always, got {kind!r}"
                    )
                if isinstance(src, str) and isinstance(dst, str) and src == dst:
                    errors.append(f"{prefix} cannot connect a step to itself")

    defaults = raw.get("defaults")
    if defaults is not None:
        if not isinstance(defaults, dict):
            errors.append("defaults must be an object")
        else:
            if "attest" in defaults and not isinstance(defaults["attest"], bool):
                errors.append("defaults.attest must be a boolean")
            fail = defaults.get("on_step_failure")
            if fail is not None and fail not in ("stop", "continue"):
                errors.append("defaults.on_step_failure must be 'stop' or 'continue'")
            for key in ("proof_profile", "proof_profile_id"):
                if key in defaults and defaults[key] is not None:
                    if not isinstance(defaults[key], str) or not str(defaults[key]).strip():
                        errors.append(f"defaults.{key} must be a non-empty string")

    if errors:
        return ValidationResult(ok=False, errors=errors, warnings=warnings)

    document = normalize_document(raw)
    return ValidationResult(ok=True, errors=[], warnings=warnings, document=document)


def normalize_document(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Return a canonical deep copy for round-trip stability."""
    doc = {
        "apiVersion": API_VERSION,
        "kind": KIND,
        "id": str(raw["id"]).strip(),
        "name": str(raw["name"]).strip(),
        "version": str(raw["version"]).strip(),
        "steps": [],
    }
    if raw.get("description") is not None:
        doc["description"] = str(raw["description"])
    if isinstance(raw.get("metadata"), dict):
        doc["metadata"] = deepcopy(raw["metadata"])
    if isinstance(raw.get("defaults"), dict):
        defaults: Dict[str, Any] = {}
        if "attest" in raw["defaults"]:
            defaults["attest"] = bool(raw["defaults"]["attest"])
        if "on_step_failure" in raw["defaults"]:
            defaults["on_step_failure"] = raw["defaults"]["on_step_failure"]
        # Proof Studio binding (APXV-PROOF-*)
        pp = raw["defaults"].get("proof_profile") or raw["defaults"].get(
            "proof_profile_id"
        )
        if isinstance(pp, str) and pp.strip():
            defaults["proof_profile"] = pp.strip()
        if defaults:
            doc["defaults"] = defaults
    if raw.get("requires_apxv") is not None:
        doc["requires_apxv"] = str(raw["requires_apxv"])

    if isinstance(raw.get("edges"), list):
        edges_out: List[Dict[str, Any]] = []
        for edge in raw["edges"]:
            if not isinstance(edge, dict):
                continue
            src = str(edge.get("from") or "").strip()
            dst = str(edge.get("to") or "").strip()
            if not src or not dst:
                continue
            entry_e: Dict[str, Any] = {
                "from": src,
                "to": dst,
                "kind": edge.get("kind")
                if edge.get("kind") in EDGE_KINDS
                else "success",
            }
            if edge.get("id"):
                entry_e["id"] = str(edge["id"])
            edges_out.append(entry_e)
        if edges_out:
            doc["edges"] = edges_out

    for step in raw["steps"]:
        entry: Dict[str, Any] = {
            "id": str(step["id"]).strip(),
            "name": str(step["name"]).strip(),
            "uses": str(step["uses"]).strip(),
        }
        if step.get("description") is not None:
            entry["description"] = str(step["description"])
        if isinstance(step.get("config"), dict):
            entry["config"] = deepcopy(step["config"])
        if isinstance(step.get("capabilities_required"), list):
            entry["capabilities_required"] = [str(c) for c in step["capabilities_required"]]
        if step.get("on_failure") in ("stop", "continue"):
            entry["on_failure"] = step["on_failure"]
        if isinstance(step.get("timeout_seconds"), (int, float)):
            entry["timeout_seconds"] = step["timeout_seconds"]
        if isinstance(step.get("pack_profile"), str) and step["pack_profile"].strip():
            entry["pack_profile"] = step["pack_profile"].strip()
        if step.get("when") in ("always", "previous_succeeded", "previous_failed"):
            entry["when"] = step["when"]
        if isinstance(step.get("next_on_success"), str) and step["next_on_success"].strip():
            entry["next_on_success"] = step["next_on_success"].strip()
        if isinstance(step.get("next_on_failure"), str) and step["next_on_failure"].strip():
            entry["next_on_failure"] = step["next_on_failure"].strip()
        if isinstance(step.get("layout"), dict):
            entry["layout"] = deepcopy(step["layout"])
        if "enabled" in step:
            entry["enabled"] = bool(step["enabled"])
        doc["steps"].append(entry)
    return doc


def documents_semantically_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return normalize_document(a) == normalize_document(b)


# --- YAML (controlled subset) -------------------------------------------------


def _yaml_escape_scalar(value: str) -> str:
    if value == "":
        return '""'
    needs_quote = bool(re.search(r'[:#\[\]{},&*?|>!%@`]', value)) or value.strip() != value
    needs_quote = needs_quote or value.lower() in ("true", "false", "null", "yes", "no")
    needs_quote = needs_quote or value[:1] in ("'", '"')
    if "\n" in value:
        lines = value.split("\n")
        return "|\n" + "\n".join(f"  {line}" for line in lines)
    if needs_quote or " " in value:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _dump_yaml_value(value: Any, indent: int) -> List[str]:
    pad = "  " * indent
    if value is None:
        return ["null"]
    if isinstance(value, bool):
        return ["true" if value else "false"]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [str(value)]
    if isinstance(value, str):
        if "\n" in value:
            lines = value.split("\n")
            out = ["|"]
            for line in lines:
                out.append(f"{pad}  {line}")
            return out
        return [_yaml_escape_scalar(value)]
    if isinstance(value, list):
        if not value:
            return ["[]"]
        out: List[str] = []
        for item in value:
            if isinstance(item, dict):
                first = True
                for key, inner in item.items():
                    inner_lines = _dump_yaml_value(inner, indent + 2)
                    if first:
                        if isinstance(inner, (dict, list)) and inner:
                            out.append(f"{pad}- {key}:")
                            out.extend(inner_lines)
                        elif isinstance(inner, str) and "\n" in inner:
                            out.append(f"{pad}- {key}: {inner_lines[0]}")
                            out.extend(inner_lines[1:])
                        else:
                            out.append(f"{pad}- {key}: {inner_lines[0]}")
                        first = False
                    else:
                        if isinstance(inner, (dict, list)) and inner:
                            out.append(f"{pad}  {key}:")
                            out.extend(inner_lines)
                        elif isinstance(inner, str) and "\n" in inner:
                            out.append(f"{pad}  {key}: {inner_lines[0]}")
                            out.extend(inner_lines[1:])
                        else:
                            out.append(f"{pad}  {key}: {inner_lines[0]}")
            else:
                dumped = _dump_yaml_value(item, indent + 1)
                out.append(f"{pad}- {dumped[0]}")
        return out
    if isinstance(value, dict):
        if not value:
            return ["{}"]
        out = []
        for key, inner in value.items():
            inner_lines = _dump_yaml_value(inner, indent + 1)
            if isinstance(inner, (dict, list)) and inner:
                out.append(f"{pad}{key}:")
                out.extend(inner_lines)
            elif isinstance(inner, str) and "\n" in inner:
                # Block scalar: key: | then indented lines (inner_lines[0] is "|")
                out.append(f"{pad}{key}: {inner_lines[0]}")
                out.extend(inner_lines[1:])
            else:
                out.append(f"{pad}{key}: {inner_lines[0]}")
        return out
    return [_yaml_escape_scalar(str(value))]


def dump_pipeline_yaml(document: Dict[str, Any]) -> str:
    doc = normalize_document(document)
    lines = _dump_yaml_value(doc, 0)
    return "\n".join(lines).rstrip() + "\n"


def dump_pipeline_json(document: Dict[str, Any]) -> str:
    doc = normalize_document(document)
    return json.dumps(doc, indent=2, sort_keys=False) + "\n"


def _parse_scalar(raw: str) -> Any:
    s = raw.strip()
    if s in ("", "~", "null", "Null", "NULL"):
        return None
    if s in ("true", "True", "TRUE", "yes", "Yes"):
        return True
    if s in ("false", "False", "FALSE", "no", "No"):
        return False
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    return s


def load_pipeline_yaml(text: str) -> Dict[str, Any]:
    """
    Load a controlled YAML subset sufficient for Pipeline Spec v0.1 documents.
    Prefer dump_pipeline_yaml output; also accepts hand-written Spec examples.
    """
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            raise PipelineSpecError("YAML root must be a mapping")
        return data
    except ImportError:
        pass

    # Minimal fallback parser for our dumped shape and simple hand-written specs
    return _load_yaml_minimal(text)


def _load_yaml_minimal(text: str) -> Dict[str, Any]:
    """Indentation-based mapping/list parser for Pipeline Spec documents."""
    lines: List[Tuple[int, str]] = []
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        lines.append((indent, raw_line.lstrip(" ")))

    def parse_block(start: int, base_indent: int) -> Tuple[Any, int]:
        if start >= len(lines):
            return {}, start
        indent, content = lines[start]
        if indent < base_indent:
            return {}, start
        # list
        if content.startswith("- ") or content == "-":
            items: List[Any] = []
            i = start
            while i < len(lines):
                ind, cont = lines[i]
                if ind < base_indent:
                    break
                if ind > base_indent:
                    raise PipelineSpecError(f"invalid list indentation near: {cont}")
                if not (cont.startswith("- ") or cont == "-"):
                    break
                rest = cont[2:] if cont.startswith("- ") else ""
                if rest == "" or rest.endswith(":") and not rest.startswith("{"):
                    # nested mapping under list item
                    if rest.endswith(":") and rest[:-1].strip():
                        key = rest[:-1].strip()
                        child, ni = parse_block(i + 1, ind + 2)
                        if isinstance(child, dict):
                            items.append({key: None, **child} if False else {key: child} if not isinstance(child, dict) else _merge_list_map(key, child, i, ind))
                        # simpler path:
                        i = i  # placeholder rewritten below
                    # rewrite list-item object parsing properly
                    obj, ni = _parse_list_item_object(i, ind)
                    items.append(obj)
                    i = ni
                    continue
                if ":" in rest and not rest.strip().startswith("{"):
                    # inline key: value then more keys as nested
                    key, val = rest.split(":", 1)
                    key = key.strip()
                    val = val.strip()
                    if val == "":
                        nested, ni = parse_block(i + 1, ind + 2)
                        item: Dict[str, Any] = {key: nested}
                        # continue reading sibling keys at ind+2
                        j = ni
                        while j < len(lines):
                            j_ind, j_cont = lines[j]
                            if j_ind <= ind:
                                break
                            if j_ind == ind + 2 and ":" in j_cont and not j_cont.startswith("- "):
                                jk, jv = j_cont.split(":", 1)
                                jk = jk.strip()
                                jv = jv.strip()
                                if jv == "":
                                    nested2, j2 = parse_block(j + 1, ind + 4)
                                    item[jk] = nested2
                                    j = j2
                                else:
                                    item[jk] = _parse_scalar(jv)
                                    j += 1
                            else:
                                break
                        items.append(item)
                        i = j
                    else:
                        items.append({key: _parse_scalar(val)})
                        i += 1
                else:
                    items.append(_parse_scalar(rest))
                    i += 1
            return items, i

        # mapping
        mapping: Dict[str, Any] = {}
        i = start
        while i < len(lines):
            ind, cont = lines[i]
            if ind < base_indent:
                break
            if ind > base_indent:
                raise PipelineSpecError(f"invalid mapping indentation near: {cont}")
            if cont.startswith("- "):
                break
            if ":" not in cont:
                raise PipelineSpecError(f"expected key: value near: {cont}")
            key, val = cont.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val == "" or val == "|" or val == ">":
                if val in ("|", ">"):
                    # multiline gather until indent decreases
                    i += 1
                    collected: List[str] = []
                    while i < len(lines):
                        c_ind, c_cont = lines[i]
                        if c_ind <= ind:
                            break
                        collected.append(c_cont)
                        i += 1
                    mapping[key] = "\n".join(collected)
                    continue
                nested, ni = parse_block(i + 1, ind + 2)
                mapping[key] = nested
                i = ni
            else:
                mapping[key] = _parse_scalar(val)
                i += 1
        return mapping, i

    def _merge_list_map(key: str, child: Any, i: int, ind: int) -> Dict[str, Any]:
        return {key: child}

    def _parse_list_item_object(i: int, ind: int) -> Tuple[Dict[str, Any], int]:
        """Parse a list item that is a mapping (steps entries)."""
        _ind, cont = lines[i]
        assert cont.startswith("- ") or cont == "-"
        rest = cont[2:] if cont.startswith("- ") else ""
        item: Dict[str, Any] = {}
        if rest and ":" in rest:
            key, val = rest.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val == "":
                nested, ni = parse_block(i + 1, ind + 2)
                item[key] = nested
                i = ni
            else:
                item[key] = _parse_scalar(val)
                i += 1
        else:
            i += 1
        while i < len(lines):
            j_ind, j_cont = lines[i]
            if j_ind <= ind:
                break
            if j_cont.startswith("- "):
                break
            if j_ind != ind + 2:
                # deeper handled by nested parse
                if ":" in j_cont:
                    pass
            if ":" not in j_cont:
                raise PipelineSpecError(f"expected key in list item: {j_cont}")
            key, val = j_cont.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val == "":
                nested, ni = parse_block(i + 1, j_ind + 2)
                item[key] = nested
                i = ni
            else:
                item[key] = _parse_scalar(val)
                i += 1
        return item, i

    # Replace broken list path with cleaner algorithm
    return _load_yaml_clean(text)


def _load_yaml_clean(text: str) -> Dict[str, Any]:
    """
    Cleaner indentation YAML loader for Pipeline Spec.
    Supports mappings, lists of mappings, scalars, and | blocks.
    """
    raw_lines = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line:
            raise PipelineSpecError("tabs not allowed in pipeline YAML")
        indent = len(line) - len(line.lstrip(" "))
        raw_lines.append((indent, line.lstrip(" ")))

    idx = 0

    def peek() -> Optional[Tuple[int, str]]:
        return raw_lines[idx] if idx < len(raw_lines) else None

    def parse_value(min_indent: int) -> Any:
        nonlocal idx
        cur = peek()
        if cur is None:
            return None
        indent, content = cur
        if indent < min_indent:
            return None
        if content.startswith("- ") or content == "-":
            return parse_list(indent)
        return parse_map(indent)

    def parse_map(map_indent: int) -> Dict[str, Any]:
        nonlocal idx
        result: Dict[str, Any] = {}
        while idx < len(raw_lines):
            indent, content = raw_lines[idx]
            if indent < map_indent:
                break
            if indent > map_indent:
                raise PipelineSpecError(f"bad indent at: {content}")
            if content.startswith("- "):
                break
            if ":" not in content:
                raise PipelineSpecError(f"expected mapping entry: {content}")
            key, rest = content.split(":", 1)
            key = key.strip()
            rest = rest.strip()
            idx += 1
            if rest == "|" or rest == ">":
                block: List[str] = []
                while idx < len(raw_lines):
                    b_ind, b_cont = raw_lines[idx]
                    if b_ind <= map_indent:
                        break
                    block.append(b_cont)
                    idx += 1
                result[key] = "\n".join(block)
            elif rest == "":
                nxt = peek()
                if nxt is None or nxt[0] <= map_indent:
                    result[key] = None
                elif nxt[1].startswith("- ") or nxt[1] == "-":
                    result[key] = parse_list(nxt[0])
                else:
                    result[key] = parse_map(nxt[0])
            else:
                result[key] = _parse_scalar(rest)
        return result

    def parse_list(list_indent: int) -> List[Any]:
        nonlocal idx
        items: List[Any] = []
        while idx < len(raw_lines):
            indent, content = raw_lines[idx]
            if indent < list_indent:
                break
            if indent > list_indent:
                raise PipelineSpecError(f"bad list indent at: {content}")
            if not (content.startswith("- ") or content == "-"):
                break
            rest = content[2:] if content.startswith("- ") else ""
            idx += 1
            if rest == "":
                nxt = peek()
                if nxt and nxt[0] > list_indent:
                    items.append(parse_value(list_indent + 2))
                else:
                    items.append(None)
            elif ":" in rest and not (rest.startswith('"') or rest.startswith("'")):
                # first key of mapping list item
                key, val = rest.split(":", 1)
                key = key.strip()
                val = val.strip()
                item: Dict[str, Any] = {}
                if val == "":
                    nxt = peek()
                    if nxt and nxt[0] > list_indent:
                        item[key] = parse_value(list_indent + 2)
                    else:
                        item[key] = None
                else:
                    item[key] = _parse_scalar(val)
                # sibling keys at list_indent + 2
                while idx < len(raw_lines):
                    s_ind, s_cont = raw_lines[idx]
                    if s_ind <= list_indent:
                        break
                    if s_cont.startswith("- "):
                        break
                    if s_ind != list_indent + 2:
                        # nested under previous key already consumed via parse_value
                        break
                    if ":" not in s_cont:
                        raise PipelineSpecError(f"expected key in list item: {s_cont}")
                    sk, sv = s_cont.split(":", 1)
                    sk = sk.strip()
                    sv = sv.strip()
                    idx += 1
                    if sv == "":
                        nxt = peek()
                        if nxt and nxt[0] > s_ind:
                            item[sk] = parse_value(s_ind + 2)
                        else:
                            item[sk] = None
                    else:
                        item[sk] = _parse_scalar(sv)
                items.append(item)
            else:
                items.append(_parse_scalar(rest))
        return items

    root = parse_map(0)
    if not isinstance(root, dict):
        raise PipelineSpecError("YAML root must be a mapping")
    return root


def load_pipeline_text(text: str, *, fmt: Optional[str] = None) -> Dict[str, Any]:
    fmt = (fmt or "auto").lower()
    stripped = text.lstrip()
    if fmt == "json" or (fmt == "auto" and stripped.startswith("{")):
        data = json.loads(text)
        if not isinstance(data, dict):
            raise PipelineSpecError("JSON root must be an object")
        return data
    if fmt in ("yaml", "yml", "auto"):
        return load_pipeline_yaml(text)
    raise PipelineSpecError(f"unsupported format {fmt!r}")


def load_pipeline_file(path: Path) -> Dict[str, Any]:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        return load_pipeline_text(text, fmt="json")
    if suffix in (".yaml", ".yml"):
        return load_pipeline_text(text, fmt="yaml")
    return load_pipeline_text(text, fmt="auto")


def validate_and_load_file(path: Path) -> ValidationResult:
    try:
        raw = load_pipeline_file(path)
    except Exception as exc:
        return ValidationResult(ok=False, errors=[str(exc)])
    return validate_pipeline_document(raw)


def dump_pipeline(document: Dict[str, Any], *, fmt: str = "yaml") -> str:
    fmt = fmt.lower()
    if fmt == "json":
        return dump_pipeline_json(document)
    if fmt in ("yaml", "yml"):
        return dump_pipeline_yaml(document)
    raise PipelineSpecError(f"unsupported dump format {fmt!r}")
