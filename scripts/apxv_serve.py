"""
APXV — Local API Server

Air-gapped, localhost-only governed runtime API.

Usage:
  python -m scripts.apxv_serve
  python -m scripts.apxv_serve --port 8741 --bind 127.0.0.1

Endpoints:
  GET  /health              — integrity check (no auth)
  GET  /status              — runtime status (auth required)
  GET  /governance          — active governance specs (auth)
  GET  /governance/proposals — list change proposals (auth)
  POST /governance/proposals — propose spec change (auth)
  POST /governance/proposals/{id}/approve|reject|apply (auth)
  GET  /capabilities        — signed capability policy status (auth)
  GET  /backups             — list local backups (auth)
  POST /backup/create       — create backup archive (auth)
  POST /backup/restore      — restore from backup filename (auth)
  POST /pipeline/run        — queue or run pipeline (auth)
  GET  /jobs                — list recent jobs (auth)
  GET  /jobs/{id}           — job status/result (auth)
  GET  /artifacts/{id}      — read artifact by hash/id (auth)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.local_api import APXVLocalServer, DEFAULT_SERVER_CONFIG, validate_localhost_bind


def main() -> int:
    parser = argparse.ArgumentParser(description="APXV local API server (air-gapped)")
    parser.add_argument("--bind", default=None, help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Port (default: 8741)")
    args = parser.parse_args()

    if args.bind or args.port:
        config_path = ROOT / "managed" / "config" / "server.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config = (
            json.loads(config_path.read_text(encoding="utf-8"))
            if config_path.exists()
            else DEFAULT_SERVER_CONFIG.copy()
        )
        if args.bind:
            config["bind_address"] = validate_localhost_bind(args.bind)
        if args.port:
            config["port"] = args.port
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    server = APXVLocalServer(base_path=ROOT)

    host, port = server.address
    print("=" * 60)
    print("APXV Local API Server")
    print("=" * 60)
    print(f"Listening: http://{host}:{port}")
    print("Air-gapped: binds localhost only, no outbound network")
    print()
    print("Endpoints:")
    print("  GET  /health")
    print("  GET  /status            (auth)")
    print("  GET  /governance        (auth)")
    print("  GET/POST /governance/proposals (auth)")
    print("  GET  /capabilities      (auth)")
    print("  GET  /backups  POST /backup/create|restore (auth)")
    print("  POST /pipeline/run      (auth)")
    print("  GET  /jobs /jobs/{id}   (auth)")
    print("  GET  /artifacts/{id}    (auth)")
    print()
    if server.generated_key:
        print("NEW API KEY (save this — shown once):")
        print(f"  {server.generated_key}")
        print()
        print("Use header: APXV-API-KEY: <key>")
        print("         or: Authorization: Bearer <key> (legacy)")
        print("         or: X-APX-API-Key: <key> (legacy)")
        print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down APXV server...")
        return 0


if __name__ == "__main__":
    sys.exit(main())