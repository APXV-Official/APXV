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

if [[ "$FRESH" -eq 1 && -d managed ]]; then
  bak="managed.bak.$(date +%Y%m%d%H%M%S)"
  echo "Moving existing managed/ to $bak"
  mv managed "$bak"
fi

echo "[1/3] Building image (Rust + Python + ZK keys — may take several minutes)..."
"${COMPOSE[@]}" build

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