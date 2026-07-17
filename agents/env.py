"""Canonical APXV_* environment variable resolver."""

from __future__ import annotations

import os
from typing import Optional


def get_env(canonical: str, default: Optional[str] = None) -> Optional[str]:
    """Resolve an APXV_* environment variable."""
    return os.environ.get(canonical, default)