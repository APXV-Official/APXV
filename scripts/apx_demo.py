"""Deprecated shim — use `python -m scripts.apxv_demo` (removed in v1.4)."""

from __future__ import annotations

import warnings

warnings.warn(
    "scripts.apx_demo is deprecated; use python -m scripts.apxv_demo",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.apxv_demo import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
