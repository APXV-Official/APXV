#!/usr/bin/env bash
# PR-4 validation: jobs cache helpers + SSE stream endpoint.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PASS=0
FAIL=0

ok() { echo "[PASS] $*"; PASS=$((PASS + 1)); }
bad() { echo "[FAIL] $*"; FAIL=$((FAIL + 1)); }

echo "=== PR-4 jobs UI freshness verify ==="
echo "ROOT=$ROOT"
echo

for needle in patchJobsFromStreamEvent notifyPipelineQueued; do
  if grep -q "$needle" ui/apps/web/src/lib/jobs-cache.ts; then
    ok "jobs-cache: $needle"
  else
    bad "jobs-cache missing $needle"
  fi
done

if grep -q 'patchJobsFromStreamEvent' ui/apps/web/src/hooks/useJobStream.ts; then
  ok "useJobStream patches cache on SSE"
else
  bad "useJobStream missing cache patch"
fi

if grep -q 'pollMs: 500' ui/apps/web/src/hooks/useJobStream.ts; then
  ok "useJobStream faster poll interval"
else
  bad "useJobStream pollMs not tuned"
fi

if grep -q 'notifyPipelineQueued' ui/apps/web/src/pages/PipelinePage.tsx; then
  ok "PipelinePage optimistic queue"
else
  bad "PipelinePage missing notifyPipelineQueued"
fi

if grep -q 'staleTime: connected' ui/apps/web/src/pages/JobsPage.tsx; then
  ok "JobsPage dynamic staleTime"
else
  bad "JobsPage missing staleTime tuning"
fi

echo
echo "=== jobs stream endpoint (Linux) ==="
KEY_FILE=$(compgen -G "managed/config/OPERATOR-KEY-*.txt" | head -1 || true)
if [[ -z "$KEY_FILE" ]]; then
  bad "no operator key for stream auth"
else
  API_KEY=$(grep -m1 '^API Key:' "$KEY_FILE" | cut -d: -f2- | tr -d ' \r\n')
  kill_port() {
    for pid in $(lsof -ti tcp:8741 -sTCP:LISTEN 2>/dev/null); do
      kill -TERM "-${pid}" 2>/dev/null || kill -TERM "${pid}" 2>/dev/null || true
    done
    sleep 0.3
  }
  kill_port
  python3 -m scripts.apxv_serve --bind 127.0.0.1 >/tmp/apxv-pr4-serve.log 2>&1 &
  SERVE_PID=$!
  trap 'kill -TERM -$SERVE_PID 2>/dev/null || true; kill_port' EXIT

  for _ in $(seq 1 40); do
    curl -sf "http://127.0.0.1:8741/api/v2/system/health" >/dev/null 2>&1 && break
    sleep 0.25
  done

  HEADERS=$(curl -sS -D - -o /dev/null -H "Authorization: Bearer ${API_KEY}" \
    -H "APXV-API-KEY: ${API_KEY}" \
    -H "Accept: text/event-stream" \
    --max-time 3 \
    "http://127.0.0.1:8741/api/v2/jobs/stream?seconds=2&poll_ms=500" 2>/dev/null || true)

  if echo "$HEADERS" | grep -qi 'text/event-stream'; then
    ok "GET /api/v2/jobs/stream returns SSE content-type"
  else
    bad "jobs stream headers unexpected"
  fi
fi

echo
echo "=== Summary: $PASS passed, $FAIL failed ==="
[[ "$FAIL" -eq 0 ]]