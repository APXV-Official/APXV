#!/usr/bin/env bash
# APXV1 — one-command onboarding (Unix). Requires Python 3.9+ and Rust.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "============================================================"
echo "APXV1 — clone to running (v1.1.1)"
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
  echo "WARNING: Rust not found — ZK setup will fail. See docs/INSTALL-RUST.md"
  echo "Or use ./scripts/install-docker.sh"
fi

echo "[1/2] Installing Python package (dev + voice extras)..."
python3 -m pip install -e ".[dev,voice]"

echo "[2/2] Onboarding (setup, pack demo, attest, verify)..."
python3 -m scripts.onboard

echo "============================================================"
echo "Done. Optional: python3 -m scripts.setup_voice"
echo "Docs: docs/QUICKSTART.md"
echo "============================================================"