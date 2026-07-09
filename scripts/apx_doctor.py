"""Deprecated shim — use `python -m scripts.apxv_doctor` (removed in v1.4)."""

from __future__ import annotations

import warnings

warnings.warn(
    "scripts.apx_doctor is deprecated; use python -m scripts.apxv_doctor",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.apxv_doctor import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
