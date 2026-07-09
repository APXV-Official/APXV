#!/usr/bin/env bash
# APXV — Native sovereign install (Rust + bootstrap + onboard). v1.3 power-user path.
set -euo pipefail

FRESH=0
SKIP_OLLAMA=0
SKIP_VOICE=0
for arg in "$@"; do
  case "$arg" in
    --fresh) FRESH=1 ;;
    --skip-ollama) SKIP_OLLAMA=1 ;;
    --skip-voice) SKIP_VOICE=1 ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "============================================================"
echo "APXV native install-full (v1.3.0 sovereign)"
echo "Teams / no local Rust? Use: ./scripts/install-docker.sh"
echo "============================================================"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.9+ or run ./scripts/install-docker.sh"
  exit 1
fi

PY_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "Python: $PY_VERSION"

if ! command -v cargo >/dev/null 2>&1 || ! command -v rustc >/dev/null 2>&1; then
  echo "ERROR: Rust not found. Install Rust (docs/INSTALL-RUST.md) or run ./scripts/install-docker.sh"
  exit 1
fi

if ! command -v cc >/dev/null 2>&1 && ! command -v gcc >/dev/null 2>&1; then
  echo "WARNING: No C compiler (cc/gcc). Rust ZK builds need build-essential on Debian/Ubuntu."
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
  echo "python3 -m venv failed — install: sudo apt install -y python3.${PY_MINOR}-venv"
  exit 1
}

if ! python3 -m pip --version >/dev/null 2>&1; then
  ensure_venv
elif ! python3 -m pip install -e ".[dev]" --dry-run >/dev/null 2>&1; then
  ensure_venv
fi

if [[ "$FRESH" -eq 1 ]]; then
  echo "Resetting runtime state (keeping governance templates)..."
  "${PYTHON[@]}" -m scripts.fresh_reset
fi

echo "[1/5] Installing Python package (dev + voice extras)..."
"${PYTHON[@]}" -m pip install -e ".[dev,voice]"

echo "[2/5] Building Rust provers (cargo build --release)..."
(
  cd rust
  cargo build --release -p apxv-circuits -p apxv-zk
)

BOOTSTRAP_ARGS=(
  "${PYTHON[@]}" -m scripts.apxv_bootstrap
  --profile production
  --skip-smoke
)
if [[ "$SKIP_OLLAMA" -eq 1 ]]; then BOOTSTRAP_ARGS+=(--skip-ollama); fi
if [[ "$SKIP_VOICE" -eq 1 ]]; then BOOTSTRAP_ARGS+=(--skip-voice); fi

echo "[3/5] Sovereign bootstrap (ZK keys + optional Ollama/Vosk)..."
echo "      First run may take several minutes (11-circuit trusted setup)."
set +e
"${BOOTSTRAP_ARGS[@]}"
bootstrap_exit=$?
set -e
if [[ "$bootstrap_exit" -eq 2 ]]; then
  echo "  Note: sovereign setup OK; optional integrations incomplete (exit 2)."
elif [[ "$bootstrap_exit" -ne 0 ]]; then
  echo "ERROR: apxv_bootstrap failed (exit $bootstrap_exit)" >&2
  exit "$bootstrap_exit"
fi

echo "[4/5] Onboarding (pack demo + attest + verify)..."
"${PYTHON[@]}" -m scripts.onboard --skip-setup

echo "[5/5] Complete."
echo "============================================================"
echo "Native sovereign install complete."
echo "  Doctor:    python3 -m scripts.apxv_doctor"
echo "  Serve API: python3 -m scripts.apxv_serve"
echo "  Demo:      ./scripts/apxv_demo.sh"
echo "  install.json: managed/config/install.json"
echo "  Activate:  source .venv/bin/activate"
echo "============================================================"