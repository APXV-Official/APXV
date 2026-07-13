#!/usr/bin/env bash
# PR-6 validation: Pack Studio on-ramp (clone reference + templates + docs links).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PASS=0
FAIL=0

ok() { echo "[PASS] $*"; PASS=$((PASS + 1)); }
bad() { echo "[FAIL] $*"; FAIL=$((FAIL + 1)); }

echo "=== PR-6 Pack Studio on-ramp verify ==="
echo "ROOT=$ROOT"
echo

for needle in REFERENCE_PACK_ID defaultQuickCloneId PACK_TUTORIAL_URL; do
  if grep -q "$needle" ui/apps/web/src/lib/pack-studio.ts; then
    ok "pack-studio: $needle"
  else
    bad "pack-studio missing $needle"
  fi
done

if grep -q 'PackStudioOnRamp' ui/apps/web/src/components/PackStudioOnRamp.tsx; then
  ok "PackStudioOnRamp component present"
else
  bad "PackStudioOnRamp component missing"
fi

if grep -q 'Duplicate reference pack' ui/apps/web/src/components/PackStudioOnRamp.tsx; then
  ok "on-ramp duplicate CTA"
else
  bad "on-ramp missing duplicate CTA"
fi

if grep -q 'BUILD-YOUR-FIRST-PACK' ui/apps/web/src/components/PackStudioOnRamp.tsx; then
  ok "tutorial link in on-ramp"
else
  bad "on-ramp missing tutorial link"
fi

if grep -q 'quickCloneReferenceMutation' ui/apps/web/src/pages/PacksPage.tsx; then
  ok "PacksPage quick clone mutation"
else
  bad "PacksPage missing quickCloneReferenceMutation"
fi

if grep -q 'openCreateForm' ui/apps/web/src/pages/PacksPage.tsx; then
  ok "PacksPage template create helper"
else
  bad "PacksPage missing openCreateForm"
fi

if grep -q 'Duplicate reference pack above' ui/apps/web/src/pages/PacksPage.tsx; then
  ok "PacksPage empty state on-ramp hint"
else
  bad "PacksPage empty state missing on-ramp hint"
fi

echo
echo "=== API clone reference pack (Linux) ==="
KEY_FILE=$(compgen -G "managed/config/OPERATOR-KEY-*.txt" | head -1 || true)
if [[ -z "$KEY_FILE" ]]; then
  bad "no operator key for clone auth"
else
  API_KEY=$(grep -m1 '^API Key:' "$KEY_FILE" | cut -d: -f2- | tr -d ' \r\n')
  kill_port() {
    for pid in $(lsof -ti tcp:8741 -sTCP:LISTEN 2>/dev/null); do
      kill -TERM "-${pid}" 2>/dev/null || kill -TERM "${pid}" 2>/dev/null || true
    done
    sleep 0.3
  }
  kill_port
  python3 -m scripts.apxv_serve --bind 127.0.0.1 >/tmp/apxv-pr6-serve.log 2>&1 &
  SERVE_PID=$!
  trap 'kill -TERM -$SERVE_PID 2>/dev/null || true; kill_port' EXIT

  for _ in $(seq 1 40); do
    curl -sf "http://127.0.0.1:8741/api/v2/system/health" >/dev/null 2>&1 && break
    sleep 0.25
  done

  SUFFIX=$(date +%s | tail -c 5)
  CLONE_ID="apxv-pack-pr6-verify-${SUFFIX}"
  BODY=$(printf '{"pack_id":"%s","name":"Pack Studio Verify Clone","description":"Pack Studio clone verification"}' "$CLONE_ID")

  RESP=$(curl -sS -w '\n%{http_code}' -X POST \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "APXV-API-KEY: ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$BODY" \
    "http://127.0.0.1:8741/api/v2/packs/apxv-pack-reference-redaction/clone" 2>/dev/null || true)

  HTTP_CODE=$(echo "$RESP" | tail -1)
  JSON=$(echo "$RESP" | sed '$d')

  if [[ "$HTTP_CODE" == "201" ]] && echo "$JSON" | grep -qF "\"pack_id\"" && echo "$JSON" | grep -qF "$CLONE_ID"; then
    ok "POST /api/v2/packs/.../clone returns 201 + pack_id"
  else
    bad "clone failed (http=$HTTP_CODE): $JSON"
  fi

  if [[ -d "governance-libraries/${CLONE_ID}" ]]; then
    ok "clone directory on disk: governance-libraries/${CLONE_ID}"
  else
    bad "clone directory missing: governance-libraries/${CLONE_ID}"
  fi
fi

echo
echo "=== Summary: $PASS passed, $FAIL failed ==="
[[ "$FAIL" -eq 0 ]]