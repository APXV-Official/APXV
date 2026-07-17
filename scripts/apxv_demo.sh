#!/usr/bin/env bash
# APXV — pack demo, attest, verify (instance must already be set up).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PACK="reference"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pack)
      PACK="${2:-}"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [--pack reference|document|ai|all]"
      echo "Runs pack demo(s), run_apxv --attest, verify_attestation --real-zk."
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: $0 [--pack reference|document|ai|all]" >&2
      exit 1
      ;;
  esac
done

PYTHON=(python3)
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON=("$ROOT/.venv/bin/python")
fi

exec "${PYTHON[@]}" -m scripts.apxv_demo --pack "$PACK"