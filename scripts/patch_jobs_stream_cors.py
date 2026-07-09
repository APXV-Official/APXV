#!/usr/bin/env python3
"""
Patch installed APXV runtime: add CORS headers to GET /api/v2/jobs/stream.

v1.3.0 desktop builds omit CORS on the SSE jobs relay. The Tauri webview then
shows "Connecting… · Failed to fetch" on the Jobs page while REST polling and
pipelines still work.

Note: Linux "Load failed" on Connect needs a desktop rebuild with
tauri-plugin-http (mixed HTTPS UI → HTTP API). This script alone does not fix that.

Usage (from your APXV data root, or pass --base-path):
  python3 -m scripts.patch_jobs_stream_cors
  python3 -m scripts.patch_jobs_stream_cors --base-path ~/.local/share/APXV

After patching: fully quit APXV (tray → Quit) and reopen.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BEGIN_EVENT_STREAM = '''
    def begin_event_stream(self) -> None:
        """Start an SSE response with CORS headers (required for browser/Tauri fetch)."""
        self.handler.send_response(200)
        self.handler.send_header("Content-Type", "text/event-stream")
        self.handler.send_header("Cache-Control", "no-cache")
        self.handler.send_header("Connection", "keep-alive")
        self.handler.send_header("X-Request-Id", self.request_id)
        self.handler.send_header(
            "Access-Control-Allow-Origin",
            resolve_cors_origin(self.handler.headers.get("Origin", "")),
        )
        self.handler.send_header("Access-Control-Allow-Headers", CORS_ALLOW_HEADERS)
        self.handler.end_headers()

'''

OLD_STREAM_HEADERS = """    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.send_header("X-Request-Id", ctx.request_id)
    handler.end_headers()"""

NEW_STREAM_HEADERS = "    ctx.begin_event_stream()"


def default_base_path() -> Path:
    if env := os.environ.get("APXV_ROOT", "").strip():
        return Path(env).expanduser().resolve()
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            return Path(local) / "APXV"
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    if xdg:
        return Path(xdg).expanduser() / "APXV"
    return Path.home() / ".local" / "share" / "APXV"


def patch_context(context_path: Path) -> str:
    text = context_path.read_text(encoding="utf-8")
    if "def begin_event_stream" in text:
        return "already patched"
    anchor = "    def send_json("
    if anchor not in text:
        raise RuntimeError(f"Unexpected {context_path} layout — cannot patch")
    updated = text.replace(anchor, BEGIN_EVENT_STREAM + anchor, 1)
    context_path.write_text(updated, encoding="utf-8")
    return "patched"


def patch_router(router_path: Path) -> str:
    text = router_path.read_text(encoding="utf-8")
    if "ctx.begin_event_stream()" in text:
        return "already patched"
    if OLD_STREAM_HEADERS not in text:
        raise RuntimeError(f"Unexpected {router_path} layout — cannot patch")
    updated = text.replace(OLD_STREAM_HEADERS, NEW_STREAM_HEADERS, 1)
    router_path.write_text(updated, encoding="utf-8")
    return "patched"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-path",
        type=Path,
        default=None,
        help="APXV data root (default: platform install location)",
    )
    args = parser.parse_args()
    base = (args.base_path or default_base_path()).resolve()

    context_path = base / "agents" / "api_v2" / "context.py"
    router_path = base / "agents" / "api_v2" / "router.py"
    for path in (context_path, router_path):
        if not path.is_file():
            print(f"Missing {path}", file=sys.stderr)
            print("Set --base-path to your APXV data root (e.g. ~/.local/share/APXV).", file=sys.stderr)
            return 1

    ctx_result = patch_context(context_path)
    router_result = patch_router(router_path)
    print(f"Base path: {base}")
    print(f"  context.py: {ctx_result}")
    print(f"  router.py:  {router_result}")
    print()
    print("Quit APXV completely (system tray → Quit), then reopen.")
    print("Jobs page should show Live updates instead of Failed to fetch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())