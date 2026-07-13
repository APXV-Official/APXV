#!/usr/bin/env bash
# Local CI parity run (matches .github/workflows/ci.yml). No git push.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.cargo/bin:${PATH}"
export APXV_VOICE_MODE=simulated
export APXV_PROFILE=ci

log() { echo ""; echo "=== $* ==="; }

ensure_ci_venv() {
  local venv="$1"
  if [[ -x "${venv}/bin/python" && -x "${venv}/bin/pip" ]]; then
    return 0
  fi
  if [[ -d "$venv" ]]; then
    rm -rf "$venv"
  fi
  if python3 -m venv "$venv" 2>/dev/null && [[ -x "${venv}/bin/pip" ]]; then
    return 0
  fi
  # WSL/Debian often lacks python3-venv (ensurepip); bootstrap pip manually.
  rm -rf "$venv"
  python3 -m venv --without-pip "$venv"
  if "${venv}/bin/python" -m ensurepip --upgrade -q 2>/dev/null; then
    return 0
  fi
  local get_pip="/tmp/apxv-get-pip.py"
  curl -fsSL https://bootstrap.pypa.io/get-pip.py -o "$get_pip"
  "${venv}/bin/python" "$get_pip" -q
}

log "Install package (venv)"
VENV="${ROOT}/.ci-venv"
ensure_ci_venv "$VENV"
# shellcheck source=/dev/null
source "${VENV}/bin/activate"
python -m pip install -q -U pip
python -m pip install -q -e ".[dev,voice]"

log "Build Rust workspace (release)"
(cd rust && cargo build --release -p apxv-circuits -p apxv-zk)

log "Run Rust tests"
(cd rust && cargo test -p apxv-circuits -p apxv-zk -q)

log "Sovereign bootstrap (CI profile)"
python -m scripts.apxv_bootstrap \
  --profile ci \
  --skip-ollama \
  --skip-voice \
  --skip-smoke \
  --skip-prover-build

log "Ceremony transcript (Tier B)"
python -m scripts.ceremony_transcript --write --tier B --note "local CI parity"
python -m scripts.ceremony_transcript --verify

log "Doctor check"
python -m scripts.apxv_doctor

log "Integrity check"
python -m scripts.apxv_ctl integrity

log "pytest"
python -m pytest tests/ -q --tb=line

log "CI parity PASS"