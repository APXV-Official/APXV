"""Deprecated shim — use auditor.apxv_verify (removed in v1.4)."""

from __future__ import annotations

import warnings

warnings.warn(
    "auditor.apx_verify is deprecated; use auditor.apxv_verify",
    DeprecationWarning,
    stacklevel=2,
)

from auditor.apxv_verify import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
