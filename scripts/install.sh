#!/usr/bin/env bash
# APXV1 — one-command onboarding (Unix). Requires Python 3.9+ and Rust.
set -euo pipefail

FRESH=0
if [[ "${1:-}" == "--fresh" ]]; then
  FRESH=1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "============================================================"
echo "APXV1 — clone to running (v1.2.5)"
echo "No Python/Rust? Use: ./scripts/install-docker.sh"
echo "============================================================"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found."
  echo "Install Python 3.9+ or run ./scripts/install-docker.sh (Docker only)."
  exit 1
fi

PY_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "Python: $PY_VERSION"

if ! command -v cargo >/dev/null 2>&1 || ! command -v rustc >/dev/null 2>&1; then
  echo "ERROR: Rust not found. Install Rust (docs/INSTALL-RUST.md) or run ./scripts/install-docker.sh"
  exit 1
fi

if ! command -v cc >/dev/null 2>&1 && ! command -v gcc >/dev/null 2>&1; then
  echo "WARNING: No C compiler (cc/gcc) found. Rust ZK builds need build-essential."
  echo "  Ubuntu/Debian/WSL: sudo apt install -y build-essential"
fi

PYTHON=(python3)
VENV_DIR="$ROOT/.venv"

ensure_venv() {
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    PYTHON=("$VENV_DIR/bin/python")
    return 0
  fi

  echo "Creating project virtualenv (.venv)..."
  if python3 -m venv "$VENV_DIR" 2>/dev/null; then
    PYTHON=("$VENV_DIR/bin/python")
    return 0
  fi

  PY_MINOR="$(python3 -c 'import sys; print(sys.version_info.minor)')"
  echo "python3 -m venv failed — install the venv package, e.g.:"
  echo "  sudo apt install -y python3-venv"
  echo "  sudo apt install -y python3.${PY_MINOR}-venv"
  echo "ensurepip unavailable — trying venv without pip..."
  if ! python3 -m venv --without-pip "$VENV_DIR"; then
    echo "ERROR: Could not create .venv. Install: sudo apt install -y python3.${PY_MINOR}-venv"
    exit 1
  fi

  GET_PIP="$(mktemp)"
  if ! curl -fsSL https://bootstrap.pypa.io/get-pip.py -o "$GET_PIP"; then
    echo "ERROR: Could not download get-pip.py. Check network or install python3-pip."
    rm -f "$GET_PIP"
    exit 1
  fi
  "$VENV_DIR/bin/python" "$GET_PIP" -q
  rm -f "$GET_PIP"
  PYTHON=("$VENV_DIR/bin/python")
}

if ! python3 -m pip --version >/dev/null 2>&1; then
  ensure_venv
elif ! python3 -m pip install --dry-run pip >/dev/null 2>&1; then
  ensure_venv
else
  if ! python3 -m pip install -e ".[dev]" --dry-run >/dev/null 2>&1; then
    ensure_venv
  fi
fi

if [[ "$FRESH" -eq 1 ]]; then
  echo "Resetting runtime state (keeping governance templates)..."
  "${PYTHON[@]}" -m scripts.fresh_reset
fi

echo "[1/2] Installing Python package (dev + voice extras)..."
"${PYTHON[@]}" -m pip install -e ".[dev,voice]"

echo "[2/2] Onboarding (setup, pack demo, attest, verify)..."
"${PYTHON[@]}" -m scripts.onboard

echo "============================================================"
echo "Done. Activate venv: source .venv/bin/activate"
echo "Quick demo: ./scripts/apx_demo.sh"
echo "Optional: ${PYTHON[*]} -m scripts.setup_voice"
echo "Docs: docs/QUICKSTART.md"
echo "============================================================"