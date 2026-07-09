"""Deprecated shim — use `python -m scripts.apxv_ctl` (removed in v1.4)."""

from __future__ import annotations

import warnings

warnings.warn(
    "scripts.apx_ctl is deprecated; use python -m scripts.apxv_ctl",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.apxv_ctl import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
