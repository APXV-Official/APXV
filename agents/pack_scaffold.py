"""Scaffold new agent packs under governance-libraries/."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, Dict

from .pack_catalog import resolve_apxv_root

_PACK_ID_RE = re.compile(r"^apxv-pack-[a-z0-9][a-z0-9-]*$")
_TEMPLATES = frozenset({"reference", "minimal"})


def _validate_pack_id(pack_id: str) -> str:
    normalized = pack_id.strip().lower()
    if not _PACK_ID_RE.match(normalized):
        raise ValueError(
            "pack_id must match apxv-pack-<slug> (lowercase letters, numbers, hyphens)"
        )
    return normalized


def create_pack(
    base_path: Path,
    *,
    pack_id: str,
    name: str,
    description: str = "",
    template: str = "reference",
) -> Dict[str, Any]:
    """Create a new agent pack directory from a template."""
    pack_id = _validate_pack_id(pack_id)
    template = (template or "reference").strip().lower()
    if template not in _TEMPLATES:
        raise ValueError(f"Unknown template: {template}. Use reference or minimal.")

    apx_root = resolve_apxv_root(base_path)
    libs = apx_root / "governance-libraries"
    target = libs / pack_id
    if target.exists():
        raise ValueError(f"Pack already exists: {pack_id}")

    if template == "reference":
        source = libs / "apxv-pack-reference-redaction"
        if not source.is_dir():
            raise FileNotFoundError("Reference template pack not found")
        shutil.copytree(source, target)
        _rewrite_pack_identity(target, pack_id=pack_id, name=name, description=description)
        _rewrite_custom_agents(target, pack_id=pack_id, name=name)
    else:
        _write_minimal_pack(target, pack_id=pack_id, name=name, description=description)

    return {
        "pack_id": pack_id,
        "name": name,
        "path": str(target.relative_to(apx_root)).replace("\\", "/"),
        "template": template,
    }


def _rewrite_pack_identity(
    pack_dir: Path,
    *,
    pack_id: str,
    name: str,
    description: str,
) -> None:
    pack_yaml = pack_dir / "pack.yaml"
    text = pack_yaml.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        if line.startswith("pack_id:"):
            lines.append(f"pack_id: {pack_id}")
        elif line.startswith("name:"):
            lines.append(f"name: {name}")
        elif line.startswith("description:"):
            lines.append("description: >-")
            lines.append(f"  {description or f'Custom agent pack {pack_id}.'}")
        else:
            lines.append(line)
    pack_yaml.write_text("\n".join(lines) + "\n", encoding="utf-8")

    readme = pack_dir / "README.md"
    if readme.exists():
        readme.write_text(
            f"# {name}\n\n{description or 'Custom APXV agent pack.'}\n",
            encoding="utf-8",
        )


def _rewrite_custom_agents(pack_dir: Path, *, pack_id: str, name: str) -> None:
    agents_dir = pack_dir / "agents"
    custom = agents_dir / "custom_agents.py"
    ref = agents_dir / "reference_agents.py"
    if ref.exists() and not custom.exists():
        ref.rename(custom)
    if custom.exists():
        custom.write_text(
            _CUSTOM_AGENTS_TEMPLATE.format(pack_id=pack_id, name=name),
            encoding="utf-8",
        )
    demo = pack_dir / "examples" / "run_pack_demo.py"
    if demo.exists():
        demo.write_text(
            _DEMO_TEMPLATE.format(pack_id=pack_id),
            encoding="utf-8",
        )


def _write_minimal_pack(
    target: Path,
    *,
    pack_id: str,
    name: str,
    description: str,
) -> None:
    (target / "agents").mkdir(parents=True)
    (target / "examples").mkdir(parents=True)
    (target / "governance" / "rules").mkdir(parents=True)
    (target / "governance" / "workflows").mkdir(parents=True)
    (target / "governance" / "knowledge").mkdir(parents=True)
    (target / "capabilities").mkdir(parents=True)

    (target / "pack.yaml").write_text(
        f"""# APXV Agent Pack manifest
pack_id: {pack_id}
name: {name}
version: 0.1.0
requires_apxv1: ">=1.2.0"
description: >-
  {description or f'Custom agent pack {pack_id}.'}

agents:
  - id: APXV-AGENT-CUSTOM-001
    type: deterministic
    module: agents.custom_agents

governance:
  rules:
    - governance/rules/RULE-CUSTOM-001.md
  workflows:
    - governance/workflows/WORKFLOW-CUSTOM-001.md
  knowledge:
    - governance/knowledge/KB-CUSTOM-001.md
""",
        encoding="utf-8",
    )

    (target / "governance" / "rules" / "RULE-CUSTOM-001.md").write_text(
        f"# RULE-CUSTOM-001\n\nGovernance rules for {name}.\n",
        encoding="utf-8",
    )
    (target / "governance" / "workflows" / "WORKFLOW-CUSTOM-001.md").write_text(
        f"# WORKFLOW-CUSTOM-001\n\nWorkflow for {name}.\n",
        encoding="utf-8",
    )
    (target / "governance" / "knowledge" / "KB-CUSTOM-001.md").write_text(
        f"# KB-CUSTOM-001\n\nKnowledge base for {name}.\n",
        encoding="utf-8",
    )
    (target / "capabilities" / "policy-delta.json").write_text(
        '{"pack_id": "' + pack_id + '", "capabilities": []}\n',
        encoding="utf-8",
    )
    (target / "agents" / "__init__.py").write_text("", encoding="utf-8")
    (target / "agents" / "custom_agents.py").write_text(
        _CUSTOM_AGENTS_TEMPLATE.format(pack_id=pack_id, name=name),
        encoding="utf-8",
    )
    (target / "examples" / "run_pack_demo.py").write_text(
        _DEMO_TEMPLATE.format(pack_id=pack_id),
        encoding="utf-8",
    )
    (target / "README.md").write_text(
        f"# {name}\n\n{description or 'Custom APXV agent pack.'}\n",
        encoding="utf-8",
    )


_CUSTOM_AGENTS_TEMPLATE = '''"""Custom agents for {pack_id} — {name}."""

from __future__ import annotations

from typing import Optional

from agents.agent1 import RuleGovernedRedactor
from agents.agent2 import WorkflowOrchestrator
from agents.agent3 import AttestationCoordinator
from agents.runtime import APXRuntime

SAMPLE_INPUT = (
    "Contact Jane at jane@example.com or call (555) 987-6543. "
    "SSN: 987-65-4321."
)


def run_pack_pipeline(
    input_text: Optional[str] = None,
    runtime: Optional[APXRuntime] = None,
    **_: object,
) -> dict:
    """Entry point used by APXV pipeline service for this pack."""
    runtime = runtime or APXRuntime()
    text = input_text or SAMPLE_INPUT
    redactor = RuleGovernedRedactor(runtime=runtime)
    redactor_output = redactor.process_text(text)
    orchestrator = WorkflowOrchestrator(runtime=runtime)
    workflow_output = orchestrator.execute_workflow(redactor_output=redactor_output)
    coordinator = AttestationCoordinator(runtime=runtime)
    return coordinator.coordinate_attestation(workflow_output=workflow_output)[
        "attested_result"
    ]
'''

_DEMO_TEMPLATE = '''"""Pack demo runner for {pack_id}."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from agents.runtime import APXRuntime


def _load_agents():
    mod_path = Path(__file__).resolve().parents[1] / "agents" / "custom_agents.py"
    spec = importlib.util.spec_from_file_location("pack_custom_agents", mod_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load pack agents from {{mod_path}}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_agents = _load_agents()
run_pack_pipeline = _agents.run_pack_pipeline
SAMPLE_INPUT = _agents.SAMPLE_INPUT


def main() -> int:
    result = run_pack_pipeline()
    print("Pack demo:", result.get("final_status"))
    return 0 if result.get("final_status") == "ATTESTED" else 1


if __name__ == "__main__":
    sys.exit(main())
'''