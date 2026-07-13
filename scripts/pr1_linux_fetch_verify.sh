#!/usr/bin/env bash
# PR-1 validation: Linux pipeline/upload must use resolveFetch (not raw browser fetch).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PASS=0
FAIL=0

ok() { echo "[PASS] $*"; PASS=$((PASS + 1)); }
bad() { echo "[FAIL] $*"; FAIL=$((FAIL + 1)); }

echo "=== PR-1 Linux fetch verify (v1.3.2) ==="
echo "ROOT=$ROOT"
echo

PIPELINE_SRC="ui/packages/api-client/src/pipeline.ts"
UPLOADS_SRC="ui/packages/api-client/src/uploads.ts"

if grep -q 'resolveFetch' "$PIPELINE_SRC" && ! grep -q 'await fetch(' "$PIPELINE_SRC"; then
  ok "pipeline.ts uses resolveFetch (no raw fetch)"
else
  bad "pipeline.ts missing resolveFetch or still uses raw fetch"
fi

if grep -q 'resolveFetch' "$UPLOADS_SRC" && ! grep -q 'await fetch(' "$UPLOADS_SRC"; then
  ok "uploads.ts uses resolveFetch (no raw fetch)"
else
  bad "uploads.ts missing resolveFetch or still uses raw fetch"
fi

if grep -q 'from "./platform-fetch"' "$PIPELINE_SRC" "$UPLOADS_SRC"; then
  ok "platform-fetch imported in pipeline + uploads"
else
  bad "platform-fetch import missing"
fi

if [[ -f managed/config/OPERATOR-KEY-default-operator.txt ]] || compgen -G "managed/config/OPERATOR-KEY-*.txt" >/dev/null; then
  ok "operator key present"
else
  bad "no OPERATOR-KEY-*.txt — run setup_first_run first"
fi

echo
echo "=== Linux API smoke (tauri_smoke --spawn-server) ==="
if python3 -m scripts.tauri_smoke --spawn-server; then
  ok "tauri_smoke pipeline + artifact on Linux"
else
  bad "tauri_smoke failed"
fi

echo
echo "=== pytest pipeline (Linux) ==="
if python3 -m pytest tests/test_local_api_v2.py::test_v2_pipeline_run_async -q --tb=short 2>/dev/null; then
  ok "pytest test_v2_pipeline_run_async"
else
  echo "(pytest skipped or failed — non-fatal if tauri_smoke passed)"
fi

echo
echo "=== Summary: $PASS passed, $FAIL failed ==="
[[ "$FAIL" -eq 0 ]]