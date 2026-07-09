"""Sovereign bootstrap orchestrator (steps 1–9)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from scripts.bootstrap.constants import BOOTSTRAP_VERSION
import os

from scripts.bootstrap.first_run import (
    run_first_run,
    seed_governance_templates,
    seed_rust_layout,
)
from scripts.rust_bins import resolve_apxv_circuits_binary, resolve_apxv_zk_binary
from scripts.bootstrap.install_json import build_install_json, write_install_json
from scripts.bootstrap.integrations import run_ollama_integration, run_voice_integration
from scripts.bootstrap.preflight import run_preflight
from scripts.bootstrap.provers import build_provers_if_needed
from scripts.bootstrap.smoke import run_smoke
from scripts.bootstrap.zk import (
    run_entity_zk,
    run_governance_zk,
    zk_setup_timestamp,
)
from scripts.setup_first_run import verify_entity_zk_keys, verify_zk_keys


@dataclass
class BootstrapOptions:
    base_path: Path
    source_root: Path
    skip_ollama: bool = False
    skip_voice: bool = False
    skip_smoke: bool = False
    skip_prover_build: bool = False
    profile: str = "production"
    json_report: bool = False


@dataclass
class BootstrapReport:
    ok: bool
    exit_code: int
    sovereign_setup: bool
    partial: bool
    base_path: str
    bootstrap_version: str = BOOTSTRAP_VERSION
    started_at: str = ""
    completed_at: str = ""
    steps: Dict[str, Any] = field(default_factory=dict)
    install_json: Optional[Dict[str, Any]] = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "exit_code": self.exit_code,
            "sovereign_setup": self.sovereign_setup,
            "partial": self.partial,
            "base_path": self.base_path,
            "bootstrap_version": self.bootstrap_version,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "steps": self.steps,
            "install_json": self.install_json,
            "errors": self.errors,
        }


def _configure_prover_env(source_root: Path) -> Dict[str, Any]:
    """Point ZK setup at release binaries from the source tree when needed."""
    circuits = resolve_apxv_circuits_binary(source_root)
    zk = resolve_apxv_zk_binary(source_root)
    if circuits:
        os.environ["APXV_CIRCUITS_BIN"] = str(circuits)
    if zk:
        os.environ["APXV_ZK_BIN"] = str(zk)
    return {
        "apxv-circuits": str(circuits) if circuits else None,
        "apxv-zk": str(zk) if zk else None,
    }


def _optional_integration_partial(ollama: Dict[str, Any], voice: Dict[str, Any]) -> bool:
    """True when optional integrations were attempted but not verified."""
    ollama_partial = not ollama.get("skipped") and not ollama.get("verified")
    voice_partial = not voice.get("skipped") and not voice.get("enabled")
    return ollama_partial or voice_partial


def run_bootstrap(options: BootstrapOptions) -> BootstrapReport:
    """Execute sovereign bootstrap contract (V1.3-PRODUCT-SPEC §4.1)."""
    base_path = options.base_path.resolve()
    source_root = options.source_root.resolve()
    started = datetime.now(timezone.utc).isoformat()
    steps: Dict[str, Any] = {}
    errors: list[str] = []

    report = BootstrapReport(
        ok=False,
        exit_code=1,
        sovereign_setup=False,
        partial=False,
        base_path=str(base_path),
        started_at=started,
    )

    try:
        print("[1/9] Preflight")
        steps["preflight"] = run_preflight(base_path, source_root=source_root)
        if not steps["preflight"]["ok"]:
            raise RuntimeError("; ".join(steps["preflight"]["errors"]))

        print("[2/9] Prover binaries")
        steps["provers"] = build_provers_if_needed(
            source_root,
            skip_build=options.skip_prover_build,
        )
        if steps["provers"].get("status") not in ("present", "built", "skipped"):
            raise RuntimeError("Prover binaries unavailable")

        steps["rust_layout"] = seed_rust_layout(base_path, source_root)
        steps["prover_env"] = _configure_prover_env(source_root)

        print("[3/9] Governance ZK trusted setup")
        steps["governance_zk"] = run_governance_zk(base_path)

        print("[4/9] Entity ZK trusted setup")
        steps["entity_zk"] = run_entity_zk(base_path)

        print("[5/9] Runtime first-run")
        steps["seed_governance"] = seed_governance_templates(base_path, source_root)
        steps["first_run"] = run_first_run(base_path, profile=options.profile)

        print("[6/9] Ollama integration")
        steps["ollama"] = run_ollama_integration(skip=options.skip_ollama)

        print("[7/9] Voice integration")
        steps["voice"] = run_voice_integration(base_path, skip=options.skip_voice)

        zk_keys = verify_zk_keys(base_path)
        entity_keys = verify_entity_zk_keys(base_path)
        sovereign_setup = bool(zk_keys.get("ready") and entity_keys.get("ready"))
        if not sovereign_setup:
            raise RuntimeError("Sovereign setup incomplete: ZK keys not ready")

        zk_setup_at = zk_setup_timestamp(base_path)
        install_payload = build_install_json(
            base_path,
            profile=options.profile,
            zk_setup_at=zk_setup_at,
            ollama=steps["ollama"],
            voice=steps["voice"],
            sovereign_setup=True,
        )
        print("[8/9] install.json provenance")
        install_path = write_install_json(base_path, install_payload)
        steps["install_json"] = {"path": str(install_path), "sovereign_setup": True}

        if not options.skip_smoke:
            print("[9/9] Smoke checks")
            steps["smoke"] = run_smoke(base_path, source_root=source_root)
        else:
            print("[9/9] Smoke checks skipped")
            steps["smoke"] = {"skipped": True}

        partial = _optional_integration_partial(steps["ollama"], steps["voice"])
        exit_code = 2 if partial else 0

        report.ok = True
        report.exit_code = exit_code
        report.sovereign_setup = True
        report.partial = partial
        report.steps = steps
        report.install_json = install_payload
        report.completed_at = datetime.now(timezone.utc).isoformat()
        return report

    except Exception as exc:
        errors.append(str(exc))
        report.errors = errors
        report.steps = steps
        report.exit_code = 1
        report.sovereign_setup = False
        report.completed_at = datetime.now(timezone.utc).isoformat()
        return report