"""Deprecated shim — use `python -m scripts.apxv_verify_bundle` (removed in v1.4)."""

from __future__ import annotations

import warnings

warnings.warn(
    "scripts.apx_verify_bundle is deprecated; use python -m scripts.apxv_verify_bundle",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.apxv_verify_bundle import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
