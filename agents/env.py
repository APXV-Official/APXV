"""Canonical APXV_* environment variable resolver with legacy APX_* fallbacks."""

from __future__ import annotations

import logging
import os
from typing import Optional

_LOG = logging.getLogger(__name__)
_WARNED: set[str] = set()

_CANONICAL_TO_LEGACY = {
    "APXV_API_KEY": "APX_API_KEY",
    "APXV_BASE_PATH": "APX_BASE_PATH",
    "APXV_CONTAINER_BIND": "APX_CONTAINER_BIND",
    "APXV_LLM_TIMEOUT_SECONDS": "APX_LLM_TIMEOUT_SECONDS",
    "APXV_VOICE_MODE": "APX_VOICE_MODE",
    "APXV_KEYS_DIR": "APX_KEYS_DIR",
    "APXV_DEV_WARNINGS": "APX_DEV_WARNINGS",
    "APXV_API_BASE": "APX_API_BASE",
    "APXV_CIRCUITS_BIN": "APX_CIRCUITS_BIN",
    "APXV_ZK_BIN": "APX_ZK_BIN",
}


def _warn_once(canonical: str, legacy: str) -> None:
    key = f"{canonical}:{legacy}"
    if key in _WARNED:
        return
    _WARNED.add(key)
    _LOG.warning(
        "Environment variable %s is deprecated; use %s instead.",
        legacy,
        canonical,
    )


def get_env(canonical: str, default: Optional[str] = None) -> Optional[str]:
    """Resolve canonical APXV_* variable, falling back to legacy APX_* when unset."""
    value = os.environ.get(canonical)
    if value is not None:
        return value

    legacy = _CANONICAL_TO_LEGACY.get(canonical)
    if legacy is None:
        return default

    legacy_value = os.environ.get(legacy)
    if legacy_value is None:
        return default

    if canonical == "APXV_API_KEY":
        _warn_once(canonical, legacy)
    return legacy_value