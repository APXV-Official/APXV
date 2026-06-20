"""
One-time helper: extract regex patterns from legacy redaction engine.ts into Python.
Run from repo root: python scripts/extract_redaction_patterns.py
Output: agents/redaction/patterns_data.py (generated — do not hand-edit).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "PEET SDK v1.0.0" / "src" / "modules" / "redaction" / "engine.ts"
OUTPUT = ROOT / "agents" / "redaction" / "patterns_data.py"

BLOCK_RE = re.compile(
    r"\{\s*"
    r"id:\s*this\.nextId\+\+,\s*"
    r"category:\s*'([^']+)',\s*"
    r"type:\s*'([^']+)',\s*"
    r"regex:\s*/((?:\\.|[^/])+)/([gimsuy]*),\s*"
    r"replacement:\s*'(\[REDACTED_[A-Z0-9_]+\])',\s*"
    r"description:\s*'((?:\\'|[^'])*)',\s*"
    r"severity:\s*'([^']+)',\s*"
    r"enabled:\s*(true|false)",
    re.MULTILINE,
)


def to_apx_token(token: str) -> str:
    inner = token.strip("[]")
    if inner.startswith("REDACTED_"):
        suffix = inner[len("REDACTED_") :]
        return f"[REDACTED-{suffix.replace('_', '-')}]"
    return token


def js_regex_to_python(pattern: str, flags: str) -> tuple[str, int]:
    py = pattern
    py = py.replace("\\/", "/")
    py_flags = 0
    if "i" in flags:
        py_flags |= re.IGNORECASE
    if "m" in flags:
        py_flags |= re.MULTILINE
    if "s" in flags:
        py_flags |= re.DOTALL
    return py, py_flags


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Source not found: {SOURCE}")

    text = SOURCE.read_text(encoding="utf-8")
    patterns = []
    for match in BLOCK_RE.finditer(text):
        category, ptype, regex_body, flag_str, replacement, description, severity, enabled = match.groups()
        py_regex, py_flags = js_regex_to_python(regex_body, flag_str)
        patterns.append(
            {
                "category": category,
                "type": ptype,
                "regex": py_regex,
                "flags": py_flags,
                "replacement": to_apx_token(replacement),
                "description": description.replace("\\'", "'"),
                "severity": severity,
                "enabled": enabled == "true",
            }
        )

    lines = [
        '"""Auto-generated pattern definitions for APXRedactionEngine."""',
        "",
        "from __future__ import annotations",
        "",
        "import re",
        "from typing import Any, Dict, List",
        "",
        "PATTERN_DEFINITIONS: List[Dict[str, Any]] = [",
    ]
    for item in patterns:
        lines.append("    {")
        for key, value in item.items():
            if key == "regex":
                lines.append(f'        "regex": r"""{value}""",')
            elif isinstance(value, str):
                lines.append(f'        "{key}": {value!r},')
            elif key == "flags":
                flag_parts = []
                if value & re.IGNORECASE:
                    flag_parts.append("re.IGNORECASE")
                if value & re.MULTILINE:
                    flag_parts.append("re.MULTILINE")
                if value & re.DOTALL:
                    flag_parts.append("re.DOTALL")
                flag_expr = " | ".join(flag_parts) if flag_parts else "0"
                lines.append(f'        "flags": {flag_expr},')
            elif isinstance(value, bool):
                lines.append(f'        "{key}": {str(value)},')
            else:
                lines.append(f'        "{key}": {value!r},')
        lines.append("    },")
    lines.append("]")
    lines.append("")
    lines.append(f"PATTERN_COUNT = {len(patterns)}")
    lines.append("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(patterns)} patterns to {OUTPUT}")


if __name__ == "__main__":
    main()