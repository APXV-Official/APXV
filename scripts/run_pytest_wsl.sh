#!/usr/bin/env bash
# Run pytest with Rust toolchain on PATH (WSL).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.cargo/bin:${PATH}"
exec python3 -m pytest "$@"