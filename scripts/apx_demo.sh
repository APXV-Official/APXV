#!/usr/bin/env bash
# Deprecated wrapper — use scripts/apxv_demo.sh (removed in v1.4).
echo "WARNING: apx_demo.sh is deprecated; use apxv_demo.sh" >&2
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/apxv_demo.sh" "$@"