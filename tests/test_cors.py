"""CORS origin resolution for browser dev and Tauri desktop."""

from agents.cors import ALLOWED_UI_ORIGINS, resolve_cors_origin


def test_resolve_cors_origin_echoes_allowed_origins():
    for origin in ALLOWED_UI_ORIGINS:
        assert resolve_cors_origin(origin) == origin


def test_resolve_cors_origin_tauri_desktop():
    assert resolve_cors_origin("https://tauri.localhost") == "https://tauri.localhost"


def test_resolve_cors_origin_unknown_falls_back_to_vite():
    assert resolve_cors_origin("https://evil.example") == "http://127.0.0.1:5173"
    assert resolve_cors_origin("") == "http://127.0.0.1:5173"