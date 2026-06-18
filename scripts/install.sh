#!/usr/bin/env bash
# APX v1 — Cross-platform install + verify (Unix)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "============================================================"
echo "APX Install"
echo "============================================================"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.9+ first."
  exit 1
fi

PY_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "Python: $PY_VERSION"

if ! command -v cargo >/dev/null 2>&1 || ! command -v rustc >/dev/null 2>&1; then
  echo "WARNING: Rust toolchain not found. ZK setup will fail."
  echo "See docs/INSTALL-RUST.md"
fi

echo "[1/5] Installing Python package..."
python3 -m pip install -e ".[dev]"

echo "[2/5] First-run setup (includes ZK keys)..."
python3 -m scripts.setup_first_run

echo "[3/5] Doctor check..."
python3 -m scripts.apx_doctor

echo "[4/5] Pipeline + attestation..."
python3 -m scripts.run_apx --attest

echo "[5/5] Independent proof verification..."
python3 -m scripts.verify_attestation --real-zk

echo "============================================================"
echo "APX install complete."
echo "Next: python3 -m scripts.apx_serve"
echo "Docs: docs/QUICKSTART.md"
echo "============================================================"