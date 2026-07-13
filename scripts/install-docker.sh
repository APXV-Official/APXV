#!/usr/bin/env bash
# APXV — Docker-only onboarding (no local Python or Rust required).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FRESH=0
if [[ "${1:-}" == "--fresh" ]]; then
  FRESH=1
fi

echo "============================================================"
echo "APXV Docker onboarding (v1.3.0)"
echo "Requires: Docker + Docker Compose"
echo "============================================================"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker not found. Install Docker: https://docs.docker.com/get-docker/"
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "ERROR: Docker Compose not found."
  exit 1
fi

reset_apx_fresh_runtime() {
  local dirs=(
    managed/artifacts managed/audit managed/backups managed/config managed/store
    rust/apxv-circuits/keys rust/apxv-zk/keys
  )
  for d in "${dirs[@]}"; do
    if [[ -e "$d" ]]; then
      echo "Removing $d"
      rm -rf "$d"
    fi
  done
}

ensure_governance_templates() {
  local missing=0
  for d in managed/rules managed/workflows managed/knowledge; do
    if [[ ! -d "$d" ]]; then missing=1; break; fi
  done
  if [[ "$missing" -eq 0 ]]; then return 0; fi

  echo "Restoring governance templates..."
  if command -v git >/dev/null 2>&1; then
    git checkout -- managed/rules managed/workflows managed/knowledge managed/config/.gitkeep 2>/dev/null || true
    missing=0
    for d in managed/rules managed/workflows managed/knowledge; do
      if [[ ! -d "$d" ]]; then missing=1; break; fi
    done
    if [[ "$missing" -eq 0 ]]; then return 0; fi
  fi

  local pack="governance-libraries/apxv-pack-reference-redaction/governance"
  mkdir -p managed/rules managed/workflows managed/knowledge
  cp "$pack/rules/RULE-RED-001.md" managed/rules/rule1.md
  cp "$pack/workflows/WORKFLOW-RED-001.md" managed/workflows/workflow1.md
  cp "$pack/knowledge/KB-RED-001.md" managed/knowledge/knowledge1.md
}

if [[ "$FRESH" -eq 1 ]]; then
  echo "Resetting runtime state (keeping governance templates)..."
  reset_apx_fresh_runtime
fi
ensure_governance_templates

if command -v ss >/dev/null 2>&1; then
  if ss -ltn 2>/dev/null | grep -q ':8741 '; then
    echo "Port 8741 in use — stopping any existing apxv container..."
    "${COMPOSE[@]}" down || true
  fi
fi

echo "[1/4] Building image (Rust + Python — no vendor keys in image)..."
"${COMPOSE[@]}" build

echo "[2/4] Sovereign bootstrap (generates ZK keys on host volumes)..."
echo "      First run may take several minutes (11-circuit trusted setup)."
"${COMPOSE[@]}" run --rm apxv python -m scripts.apxv_bootstrap \
  --skip-ollama --skip-voice --skip-smoke --skip-prover-build

echo "[3/4] Pack demo + attest + verify..."
"${COMPOSE[@]}" run --rm apxv python -m scripts.onboard --skip-setup

echo "[4/4] Starting API server..."
docker rm -f apx-v1 2>/dev/null || true
docker rm -f apxv 2>/dev/null || true
"${COMPOSE[@]}" up -d

echo "============================================================"
echo "Docker onboarding complete."
echo "  Health:  curl http://127.0.0.1:8741/health"
echo "  Logs:    docker logs apxv"
echo "  Stop:    docker compose down"
echo "============================================================"