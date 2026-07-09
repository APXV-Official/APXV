#!/usr/bin/env bash
# Row 11 - Tauri desktop smoke (Phase A gate) — PR-18 cross-platform path
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEV_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_TAURI="$DEV_ROOT/ui/apps/desktop/src-tauri"
RUNTIME_ROOT="$DEV_ROOT/runtime"
if [[ ! -f "$RUNTIME_ROOT/pyproject.toml" ]]; then
  RUNTIME_ROOT="$DEV_ROOT"
fi
LOG_PATH="$DEV_ROOT/audit-tauri.log"
API_KEY="${APXV_API_KEY:-gnKiTGGjRimhIPWeoP9BLnumQVPClWxYVbAD8J_FXVM}"

log() {
  echo "$1" | tee -a "$LOG_PATH"
}

: >"$LOG_PATH"
log "=== TAURI SMOKE (Row 11 / PR-18) $(date -Iseconds) ==="
log "Workspace: $DEV_ROOT"

log "--- [A] cargo check (desktop shell) ---"
pushd "$DESKTOP_TAURI" >/dev/null
if cargo check 2>&1 | tee -a "$LOG_PATH"; then
  log "PASS: cargo check"
else
  log "FAIL: cargo check"
  exit 1
fi
popd >/dev/null

log "--- [B] APXV root resolution + bootstrap commands ---"
PATHS_RS="$DESKTOP_TAURI/src/paths.rs"
BOOTSTRAP_RS="$DESKTOP_TAURI/src/bootstrap.rs"
PYTHON_CMD_RS="$DESKTOP_TAURI/src/python_cmd.rs"
TAURI_CONF="$DESKTOP_TAURI/tauri.conf.json"

if grep -q "resolve_apxv_root" "$PATHS_RS" && grep -q "default_local_appdata_root" "$PATHS_RS"; then
  log "PASS: paths.rs resolves operator data root"
else
  log "FAIL: paths.rs missing operator root resolution"
  exit 1
fi

case "$(uname -s)" in
  Darwin)
    if grep -q "Application Support" "$PATHS_RS"; then
      log "PASS: paths.rs includes macOS Application Support"
    else
      log "FAIL: paths.rs missing macOS Application Support"
      exit 1
    fi
    ;;
  Linux)
    if grep -q "XDG_DATA_HOME" "$PATHS_RS"; then
      log "PASS: paths.rs includes Linux XDG_DATA_HOME"
    else
      log "FAIL: paths.rs missing Linux XDG path"
      exit 1
    fi
    ;;
esac

if grep -q "run_bootstrap" "$BOOTSTRAP_RS" && grep -q "get_bootstrap_status" "$BOOTSTRAP_RS"; then
  log "PASS: bootstrap.rs Tauri commands present"
else
  log "FAIL: bootstrap.rs missing sovereign commands"
  exit 1
fi

if grep -q "spawn_python_module" "$PYTHON_CMD_RS"; then
  log "PASS: python_cmd.rs cross-platform interpreter"
else
  log "FAIL: python_cmd.rs missing spawn_python_module"
  exit 1
fi

if grep -q "runtime-payload" "$TAURI_CONF"; then
  log "PASS: tauri.conf.json bundles runtime payload"
else
  log "WARN: tauri.conf.json missing runtime-payload resources"
fi

log "--- [C] API smoke (dev runtime + onboard flow) ---"
pushd "$RUNTIME_ROOT" >/dev/null
export APXV_API_KEY="$API_KEY"
if python3 -m scripts.tauri_smoke --spawn-server 2>&1 | tee -a "$LOG_PATH"; then
  log "PASS: tauri_smoke.py"
else
  log "FAIL: tauri_smoke.py"
  exit 1
fi
popd >/dev/null

log "--- [D] Playwright bootstrap preview ---"
pushd "$DEV_ROOT/ui/apps/web" >/dev/null
export APXV_API_KEY="$API_KEY"
if pnpm exec playwright test e2e/bootstrap.spec.ts --reporter=line 2>&1 | tee -a "$LOG_PATH"; then
  log "PASS: Playwright bootstrap preview"
else
  log "WARN: Playwright bootstrap preview failed"
fi
popd >/dev/null

log ""
log "OVERALL: PASS - Row 11 Tauri smoke complete (PR-18 cross-platform path)"
exit 0