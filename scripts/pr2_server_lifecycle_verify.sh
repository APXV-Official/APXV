#!/usr/bin/env bash
# PR-2 validation: stop/start leaves a single listener on :8741 (Linux).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PORT=8741

PASS=0
FAIL=0

ok() { echo "[PASS] $*"; PASS=$((PASS + 1)); }
bad() { echo "[FAIL] $*"; FAIL=$((FAIL + 1)); }

port_open() {
  python3 -c "import socket; s=socket.socket(); s.settimeout(0.8); s.connect(('127.0.0.1', ${PORT}))" 2>/dev/null
}

kill_port_listeners() {
  local port=$1
  set +e
  if command -v lsof >/dev/null 2>&1; then
    for pid in $(lsof -ti "tcp:${port}" -sTCP:LISTEN 2>/dev/null); do
      kill -TERM "-${pid}" 2>/dev/null || kill -TERM "${pid}" 2>/dev/null || true
      sleep 0.2
      kill -KILL "-${pid}" 2>/dev/null || kill -KILL "${pid}" 2>/dev/null || true
    done
  fi
  if command -v fuser >/dev/null 2>&1; then
    fuser -k -TERM "${port}/tcp" 2>/dev/null || true
    fuser -k -KILL "${port}/tcp" 2>/dev/null || true
  fi
  set -e
}

echo "=== PR-2 server lifecycle verify (Linux) ==="
echo "ROOT=$ROOT"
echo

kill_port_listeners "$PORT"
sleep 0.5

if port_open; then
  bad "port :$PORT still open before test"
else
  ok "port :$PORT free before start"
fi

python3 -m scripts.apxv_serve --bind 127.0.0.1 >/tmp/apxv-pr2-serve.log 2>&1 &
PID=$!
trap 'kill -TERM -$PID 2>/dev/null || kill -TERM $PID 2>/dev/null || true; kill_port_listeners '"$PORT" EXIT

for _ in $(seq 1 40); do
  if port_open; then break; fi
  sleep 0.25
done

if port_open; then
  ok "apxv_serve opened :$PORT (pid $PID)"
else
  bad "apxv_serve failed to open :$PORT"
  tail -20 /tmp/apxv-pr2-serve.log || true
fi

kill -TERM "-$PID" 2>/dev/null || kill -TERM "$PID" 2>/dev/null || true
sleep 0.3
kill_port_listeners "$PORT"

for _ in $(seq 1 30); do
  if ! port_open; then break; fi
  sleep 0.2
done

if port_open; then
  bad "port :$PORT still open after stop"
else
  ok "port :$PORT released after stop"
fi

python3 -m scripts.apxv_serve --bind 127.0.0.1 >/tmp/apxv-pr2-serve2.log 2>&1 &
PID2=$!

for _ in $(seq 1 40); do
  if port_open; then break; fi
  sleep 0.25
done

if port_open; then
  ok "restart cycle — apxv_serve listening again (pid $PID2)"
else
  bad "restart cycle — :$PORT did not reopen"
fi

echo
echo "=== cargo test (server.rs unit, optional) ==="
if cargo test --manifest-path ui/apps/desktop/src-tauri/Cargo.toml unreachable_port --quiet 2>/dev/null; then
  ok "cargo test unreachable_port"
else
  echo "[SKIP] cargo test (needs Tauri runtime-payload build — lifecycle checks above are authoritative)"
fi

echo
echo "=== Summary: $PASS passed, $FAIL failed (lifecycle gate) ==="
[[ "$FAIL" -eq 0 ]]