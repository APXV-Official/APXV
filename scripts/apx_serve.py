"""Deprecated shim — use `python -m scripts.apxv_serve` (removed in v1.4)."""

from __future__ import annotations

import warnings

warnings.warn(
    "scripts.apx_serve is deprecated; use python -m scripts.apxv_serve",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.apxv_serve import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
