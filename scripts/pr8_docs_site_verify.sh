#!/usr/bin/env bash
# Pre-promotion docs/site consistency check for v1.3.3.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PASS=0
FAIL=0

ok() { echo "[PASS] $*"; PASS=$((PASS + 1)); }
bad() { echo "[FAIL] $*"; FAIL=$((FAIL + 1)); }

echo "=== v1.3.3 docs + site verify ==="
echo "ROOT=$ROOT"
echo

for f in README.md ROADMAP.md docs/DOWNLOADS.md docs/INSTALL-USER.md website/index.html ui/docs/OPERATOR-GUIDE.md; do
  [[ -f "$f" ]] && ok "present: $f" || bad "missing: $f"
done

if grep -q 'v1.3.3' README.md && grep -q 'current release' README.md; then
  ok "README current release v1.3.3"
else
  bad "README release line"
fi

if grep -q 'releases/latest' README.md docs/DOWNLOADS.md docs/INSTALL-USER.md website/index.html; then
  ok "releases/latest links"
else
  bad "missing releases/latest"
fi

if grep -q 'APXV™' README.md NOTICE website/index.html; then
  ok "APXV™ trademark surfaces"
else
  bad "trademark missing"
fi

if grep -q 'id="download"' website/index.html; then
  ok "website download section"
else
  bad "website #download"
fi

if grep -q 'Shipped — v1.3.3 (current)' website/index.html; then
  ok "website roadmap v1.3.3 current"
else
  bad "website roadmap stale"
fi

if grep -q '1.3.3' ui/packages/types/src/index.ts; then
  ok "APXV_UI_VERSION 1.3.3"
else
  bad "APXV_UI_VERSION"
fi

if grep -q 'default="v1.3.3"' scripts/publish_github_release.py; then
  ok "publish_github_release default tag"
else
  bad "publish script tag"
fi

if grep -q '## \[1.3.3\]' CHANGELOG.md; then
  ok "CHANGELOG 1.3.3 section"
else
  bad "CHANGELOG missing 1.3.3"
fi

stale=0
if grep -qE 'Current release.*\[v1\.3\.[012]\]' README.md 2>/dev/null; then stale=1; fi
if grep -qE 'Current release on site:.*v1\.3\.[012]' website/README.md 2>/dev/null; then stale=1; fi
if grep -qE 'operator console for APXV v1\.3\.[012]' ui/README.md 2>/dev/null; then stale=1; fi
if grep -qE 'v1\.3\.[012] ships \*\*Windows MSI' ui/apps/desktop/README.md 2>/dev/null; then stale=1; fi
if [[ "$stale" -eq 1 ]]; then
  bad "stale current-release marker"
else
  ok "no stale current-release markers"
fi

if grep -q 'Settings Start/Restart' ROADMAP.md && grep -q 'Runtime process' docs/INSTALL-USER.md; then
  ok "lifecycle docs mention Settings controls"
else
  bad "lifecycle Settings docs incomplete"
fi

echo
echo "=== Summary: $PASS passed, $FAIL failed ==="
[[ "$FAIL" -eq 0 ]]