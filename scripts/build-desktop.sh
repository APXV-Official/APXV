#!/usr/bin/env bash
# Build APXV desktop installer for the current OS (dmg/app, deb/appimage, or msi/nsis).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEV_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNTIME_ROOT="$DEV_ROOT/runtime"
if [[ ! -f "$RUNTIME_ROOT/pyproject.toml" ]]; then
  RUNTIME_ROOT="$DEV_ROOT"
fi
RUST_DIR="$RUNTIME_ROOT/rust"
UI_ROOT="$DEV_ROOT/ui"
TAURI_ROOT="$UI_ROOT/apps/desktop/src-tauri"

# shellcheck source=/dev/null
source "$SCRIPT_DIR/wsl-env.sh" 2>/dev/null || true
if ! command -v node >/dev/null 2>&1; then
  echo "FAIL: node not found. Install Node 20+ in WSL (apt install nodejs) or on Windows."
  exit 1
fi
if ! command -v pnpm >/dev/null 2>&1; then
  echo "FAIL: pnpm not found. Install: npm install -g pnpm"
  exit 1
fi

if [[ ! -f "$RUST_DIR/Cargo.toml" ]]; then
  echo "FAIL: Rust workspace not found at $RUST_DIR"
  exit 1
fi

if [[ "${APXV_SKIP_PROVER_BUILD:-}" != "1" ]]; then
  echo "Building release prover binaries for $(uname -s)..."
  pushd "$RUST_DIR" >/dev/null
  cargo build --release -p apxv-circuits -p apxv-zk
  popd >/dev/null
else
  echo "Skipping prover build (APXV_SKIP_PROVER_BUILD=1)."
fi

echo "Staging runtime payload..."
bash "$SCRIPT_DIR/stage-desktop-runtime.sh"

pushd "$UI_ROOT" >/dev/null
if [[ "${APXV_SKIP_WEB_BUILD:-}" == "1" && -f apps/web/dist/index.html ]]; then
  echo "Using prebuilt web dist (APXV_SKIP_WEB_BUILD=1)."
else
  echo "Building APXV web assets..."
  if [[ ! -d node_modules ]]; then
    echo "Installing UI dependencies (first run)..."
    pnpm install
  fi
  pnpm --filter @apxv/web build
fi
# Invoke tauri directly from apps/desktop (same path Linux CI uses).
# Avoid pnpm --filter @apxv/desktop build on Windows — package prebuild + filter is unreliable in GHA.
if [[ ! -d node_modules ]]; then
  pnpm install
fi
pushd apps/desktop >/dev/null
if [[ -n "${APXV_WINDOWS_BUNDLES:-}" ]]; then
  echo "  bundles: $APXV_WINDOWS_BUNDLES"
  pnpm exec -- tauri build --verbose --bundles "$APXV_WINDOWS_BUNDLES"
else
  pnpm exec -- tauri build --verbose
fi
popd >/dev/null
popd >/dev/null

echo ""
echo "Build complete."
case "$(uname -s)" in
  Darwin)
    APP="$TAURI_ROOT/target/release/bundle/macos/APXV.app"
    DMG_DIR="$TAURI_ROOT/target/release/bundle/dmg"
    [[ -d "$APP" ]] && echo "  App:  $APP"
    ls "$DMG_DIR"/*.dmg 2>/dev/null | while read -r f; do echo "  DMG:  $f"; done
    ;;
  Linux)
    DEB_DIR="$TAURI_ROOT/target/release/bundle/deb"
    APPIMAGE_DIR="$TAURI_ROOT/target/release/bundle/appimage"
    ls "$DEB_DIR"/*.deb 2>/dev/null | while read -r f; do echo "  Deb:  $f"; done
    ls "$APPIMAGE_DIR"/*.AppImage 2>/dev/null | while read -r f; do echo "  AppImage: $f"; done
    ;;
  MINGW*|MSYS*|CYGWIN*|Windows_NT)
    ls "$TAURI_ROOT/target/release/bundle/msi/"*.msi 2>/dev/null | while read -r f; do echo "  MSI:  $f"; done
    ls "$TAURI_ROOT/target/release/bundle/nsis/"*setup.exe 2>/dev/null | while read -r f; do echo "  Setup: $f"; done
    ;;
  *)
    echo "  Binary: $TAURI_ROOT/target/release/apxv"
    ;;
esac

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*|Windows_NT)
    [[ -f "$TAURI_ROOT/target/release/apxv.exe" ]] || { echo "FAIL: apxv.exe missing" >&2; exit 1; }
    ls "$TAURI_ROOT/target/release/bundle/msi/"*.msi >/dev/null 2>&1 || { echo "FAIL: MSI missing" >&2; exit 1; }
    ls "$TAURI_ROOT/target/release/bundle/nsis/"*setup.exe >/dev/null 2>&1 || { echo "FAIL: NSIS setup missing" >&2; exit 1; }
    ;;
esac