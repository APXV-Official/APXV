#!/usr/bin/env bash
# PR-3 validation: operator key hint endpoint + discovery prerequisites.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PASS=0
FAIL=0

ok() { echo "[PASS] $*"; PASS=$((PASS + 1)); }
bad() { echo "[FAIL] $*"; FAIL=$((FAIL + 1)); }

echo "=== PR-3 onboarding / API key verify ==="
echo "ROOT=$ROOT"
echo

if compgen -G "managed/config/OPERATOR-KEY-*.txt" >/dev/null; then
  ok "OPERATOR-KEY hint file on disk"
else
  bad "missing OPERATOR-KEY-*.txt (run setup_first_run)"
fi

if grep -q 'discoverOperatorKey' ui/apps/web/src/lib/operator-key-discovery.ts; then
  ok "discoverOperatorKey helper present"
else
  bad "discoverOperatorKey missing"
fi

if grep -q 'OperatorKeyPanel' ui/apps/web/src/pages/SetupPage.tsx; then
  ok "SetupPage uses OperatorKeyPanel"
else
  bad "SetupPage missing OperatorKeyPanel"
fi

if grep -q 'discoverOperatorKey' ui/apps/web/src/pages/OnboardingPage.tsx; then
  ok "OnboardingPage uses discoverOperatorKey"
else
  bad "OnboardingPage missing discoverOperatorKey"
fi

if grep -q 'Test connection' ui/apps/web/src/pages/SetupPage.tsx; then
  ok "SetupPage inline test connection"
else
  bad "SetupPage missing test connection"
fi

echo
echo "=== API operator-key-hint (Linux) ==="
kill_port() {
  local port=8741
  for pid in $(lsof -ti "tcp:${port}" -sTCP:LISTEN 2>/dev/null); do
    kill -TERM "-${pid}" 2>/dev/null || kill -TERM "${pid}" 2>/dev/null || true
  done
  sleep 0.3
}

kill_port
python3 -m scripts.apxv_serve --bind 127.0.0.1 >/tmp/apxv-pr3-serve.log 2>&1 &
SERVE_PID=$!
trap 'kill -TERM -$SERVE_PID 2>/dev/null || true; kill_port' EXIT

for _ in $(seq 1 40); do
  if curl -sf "http://127.0.0.1:8741/api/v2/system/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

HINT=$(curl -sf "http://127.0.0.1:8741/api/v2/system/operator-key-hint" 2>/dev/null || true)
if echo "$HINT" | grep -q '"key"'; then
  ok "GET /api/v2/system/operator-key-hint returns key"
else
  bad "operator-key-hint failed: $HINT"
fi

echo
echo "=== Summary: $PASS passed, $FAIL failed ==="
[[ "$FAIL" -eq 0 ]]