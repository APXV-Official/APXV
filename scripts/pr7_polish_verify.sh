#!/usr/bin/env bash
# PR-7 validation: UI polish, APXV™ notices, downloads hub.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PASS=0
FAIL=0

ok() { echo "[PASS] $*"; PASS=$((PASS + 1)); }
bad() { echo "[FAIL] $*"; FAIL=$((FAIL + 1)); }

echo "=== PR-7 polish + trademark + downloads verify ==="
echo "ROOT=$ROOT"
echo

for file in README.md NOTICE docs/DOWNLOADS.md; do
  if [[ -f "$file" ]]; then
    ok "present: $file"
  else
    bad "missing: $file"
  fi
done

if grep -q 'APXV™' README.md; then
  ok "README APXV™ heading"
else
  bad "README missing APXV™"
fi

if grep -q 'releases/latest' README.md; then
  ok "README releases/latest link"
else
  bad "README missing releases/latest"
fi

if grep -q 'trademark' NOTICE; then
  ok "NOTICE trademark line"
else
  bad "NOTICE missing trademark"
fi

if grep -q 'APXV™' ui/apps/desktop/src-tauri/tauri.conf.json; then
  ok "desktop window title APXV™"
else
  bad "tauri.conf missing APXV™"
fi

if grep -q 'APXV™' ui/apps/web/src/components/BrandLogo.tsx; then
  ok "BrandLogo APXV™"
else
  bad "BrandLogo missing APXV™"
fi

if grep -q 'About APXV™' ui/apps/web/src/pages/SettingsPage.tsx; then
  ok "Settings About section"
else
  bad "Settings missing About APXV™"
fi

if grep -q 'serverStatus.port_open' ui/apps/web/src/pages/SettingsPage.tsx; then
  ok "Settings structured server status"
else
  bad "Settings missing structured server status"
fi

if grep -q 'Open Settings' ui/apps/web/src/components/ConnectionBanner.tsx; then
  ok "ConnectionBanner Settings action"
else
  bad "ConnectionBanner missing Settings link"
fi

if grep -q 'OPERATOR-KEY' ui/apps/web/src/lib/api-errors.ts; then
  ok "api-errors actionable 401 hint"
else
  bad "api-errors missing actionable hints"
fi

if grep -q 'emptyAction' ui/apps/web/src/pages/JobsPage.tsx; then
  ok "JobsPage empty pipeline CTA"
else
  bad "JobsPage missing emptyAction"
fi

if grep -q 'id="download"' website/index.html; then
  ok "website download section"
else
  bad "website missing #download"
fi

if grep -q 'releases/latest' website/index.html; then
  ok "website releases/latest links"
else
  bad "website missing releases/latest"
fi

if grep -q 'DOWNLOADS.md' website/index.html; then
  ok "website DOWNLOADS.md link"
else
  bad "website missing DOWNLOADS.md link"
fi

echo
echo "=== Summary: $PASS passed, $FAIL failed ==="
[[ "$FAIL" -eq 0 ]]