"""CORS helpers for the local APXV API (browser dev + Tauri desktop)."""

from __future__ import annotations

# Vite dev server, Docker nginx UI, and Tauri 2 production webview origins.
ALLOWED_UI_ORIGINS = frozenset(
    {
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "https://tauri.localhost",
        "http://tauri.localhost",
        "tauri://localhost",
        "https://asset.localhost",
        "http://asset.localhost",
    }
)

DEFAULT_UI_ORIGIN = "http://127.0.0.1:5173"

CORS_ALLOW_HEADERS = (
    "Authorization, Content-Type, APXV-API-KEY, X-APX-API-Key, Accept"
)
CORS_ALLOW_METHODS = "GET, POST, PUT, DELETE, OPTIONS"


def resolve_cors_origin(request_origin: str) -> str:
    """Return Access-Control-Allow-Origin for a request Origin header."""
    origin = (request_origin or "").strip()
    if origin in ALLOWED_UI_ORIGINS:
        return origin
    return DEFAULT_UI_ORIGIN