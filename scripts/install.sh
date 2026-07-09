#!/usr/bin/env bash
# APXV — DEPRECATED: use install-full.sh (v1.3 sovereign) or install-docker.sh (teams).
set -euo pipefail

echo "============================================================"
echo "NOTE: install.sh is deprecated in v1.3."
echo "  Native sovereign:  ./scripts/install-full.sh"
echo "  Docker (teams):    ./scripts/install-docker.sh"
echo "============================================================"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$ROOT/install-full.sh"
if [[ ! -f "$TARGET" ]]; then
  echo "ERROR: Missing install-full.sh" >&2
  exit 1
fi

ARGS=()
if [[ "${1:-}" == "--fresh" ]]; then
  ARGS+=(--fresh)
fi

exec bash "$TARGET" "${ARGS[@]}"