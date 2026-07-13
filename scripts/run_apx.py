"""Deprecated shim — use `python -m scripts.run_apxvv` (removed in v1.4)."""

from __future__ import annotations

import warnings

warnings.warn(
    "scripts.run_apx is deprecated; use python -m scripts.run_apxvv",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.run_apxv import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
