#!/usr/bin/env bash
# Build APXV desktop installer for the current OS (dmg/app, deb/appimage, or msi/nsis).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEV_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
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

echo "Building release prover binaries for $(uname -s)..."
pushd "$DEV_ROOT/runtime/rust" >/dev/null
cargo build --release -p apxv-circuits -p apxv-zk
popd >/dev/null

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
if [[ "$(uname -s)" == "Linux" ]]; then
  # prebuild in package.json is Windows-only (powershell); staging already ran above.
  if [[ ! -d node_modules ]]; then
    pnpm install
  fi
  pushd apps/desktop >/dev/null
  pnpm exec tauri build
  popd >/dev/null
else
  pnpm --filter @apxv/desktop build
fi
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
  *)
    echo "  Binary: $TAURI_ROOT/target/release/apxv"
    ;;
esac