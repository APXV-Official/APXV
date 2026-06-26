#!/usr/bin/env bash
# APXV1 — Docker-only onboarding (no local Python or Rust required).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FRESH=0
if [[ "${1:-}" == "--fresh" ]]; then
  FRESH=1
fi

echo "============================================================"
echo "APXV1 Docker onboarding (v1.1.1)"
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
    rust/apx-circuits/keys rust/apx-zk/keys
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
    echo "Port 8741 in use — stopping any existing apx-v1 container..."
    "${COMPOSE[@]}" down || true
  fi
fi

seed_zk_keys_from_image() {
  local circuits_keys="rust/apx-circuits/keys"
  local zk_keys="rust/apx-zk/keys"
  local circuits_empty=0 zk_empty=0
  if [[ ! -d "$circuits_keys" ]] || [[ -z "$(ls -A "$circuits_keys" 2>/dev/null)" ]]; then
    circuits_empty=1
  fi
  if [[ ! -d "$zk_keys" ]] || [[ -z "$(ls -A "$zk_keys" 2>/dev/null)" ]]; then
    zk_empty=1
  fi
  if [[ "$circuits_empty" -eq 0 && "$zk_empty" -eq 0 ]]; then
    return 0
  fi

  echo "Seeding ZK keys from image (volume mounts hide baked-in keys)..."
  mkdir -p rust/apx-circuits rust/apx-zk
  cid="$(docker create apx-v1:latest)"
  docker cp "${cid}:/app/rust/apx-circuits/keys" rust/apx-circuits/
  docker cp "${cid}:/app/rust/apx-zk/keys" rust/apx-zk/
  docker rm "$cid" >/dev/null
}

echo "[1/3] Building image (Rust + Python + ZK keys — may take several minutes)..."
"${COMPOSE[@]}" build
seed_zk_keys_from_image

echo "[2/3] Onboarding in container (pack demo, attest, verify)..."
"${COMPOSE[@]}" run --rm apx-v1 python -m scripts.onboard --skip-zk

echo "[3/3] Starting API server..."
"${COMPOSE[@]}" up -d

echo "============================================================"
echo "Docker onboarding complete."
echo "  Health:  curl http://127.0.0.1:8741/health"
echo "  Logs:    docker logs apx-v1"
echo "  Stop:    docker compose down"
echo "============================================================"