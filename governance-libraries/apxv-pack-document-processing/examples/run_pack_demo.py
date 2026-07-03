"""Document Processing Pack — batch folder demo."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

DEFAULT_BATCH_DIR = Path(__file__).resolve().parent / "inputs" / "batch"
# Canonical demo fixtures — ignore stray files in the default batch folder (F-020).
DEMO_BATCH_FILES = ("invoice.txt", "customer.json")


def _load_document_agents():
    mod_path = Path(__file__).resolve().parents[1] / "agents" / "document_agents.py"
    spec = importlib.util.spec_from_file_location("pack_document_agents", mod_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load pack agents from {mod_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_doc = _load_document_agents()
process_batch_directory = _doc.process_batch_directory


def main() -> int:
    batch_dir = DEFAULT_BATCH_DIR
    if len(sys.argv) > 1:
        batch_dir = Path(sys.argv[1]).resolve()

    only_files = None
    if batch_dir.resolve() == DEFAULT_BATCH_DIR.resolve():
        only_files = DEMO_BATCH_FILES

    result = process_batch_directory(batch_dir, only_files=only_files)
    status = result.get("final_status")
    output = result.get("proposed_artifact", {}).get("output", {})
    redactions = output.get("total_redactions", 0)
    manifest = output.get("batch_manifest", {})
    file_count = manifest.get("file_count", 0)
    policy_id = output.get("compliance_policy_id")

    print(
        "Pack demo complete: "
        f"final_status={status}, file_count={file_count}, "
        f"total_redactions={redactions}, compliance_policy_id={policy_id}"
    )

    if status != "ATTESTED":
        return 1
    if file_count < 2:
        return 1
    if redactions < 1:
        return 1
    if policy_id != 2:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())