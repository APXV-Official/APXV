"""Multi-format detection and parsing for structured redaction."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, List, Literal, Union

FormatName = Literal["json", "xml", "csv", "yaml", "text"]

MAX_FORMAT_INPUT_LENGTH = 500_000


@dataclass
class ParsedData:
    data: Any
    original_format: FormatName


class FormatParser:
    def detect_format(self, input_text: str) -> FormatName:
        if len(input_text) > MAX_FORMAT_INPUT_LENGTH:
            return "text"

        trimmed = input_text.strip()

        if (trimmed.startswith("{") and trimmed.endswith("}")) or (
            trimmed.startswith("[") and trimmed.endswith("]")
        ):
            try:
                json.loads(trimmed)
                return "json"
            except json.JSONDecodeError:
                pass

        if trimmed.startswith("<") and trimmed.endswith(">"):
            return "xml"

        lines = [line for line in trimmed.split("\n") if line.strip()]
        if len(lines) > 1 and "," in lines[0]:
            first_line = lines[0]
            if "{" not in first_line and "[" not in first_line:
                first_commas = first_line.count(",")
                matching = 0
                for line in lines[1 : min(len(lines), 5)]:
                    if line.count(",") == first_commas:
                        matching += 1
                if first_commas > 0 and matching >= 2:
                    return "csv"

        yaml_lines = len(re.findall(r"^[\w-]+:\s*.+", trimmed, flags=re.MULTILINE))
        if trimmed.startswith("---") or yaml_lines >= 2:
            return "yaml"

        return "text"

    def parse(self, input_text: str) -> ParsedData:
        fmt = self.detect_format(input_text)
        if fmt == "json":
            return ParsedData(data=json.loads(input_text), original_format="json")
        if fmt == "xml":
            return ParsedData(data=self._parse_xml(input_text), original_format="xml")
        if fmt == "csv":
            return ParsedData(data=self._parse_csv(input_text), original_format="csv")
        if fmt == "yaml":
            return ParsedData(data=self._parse_yaml(input_text), original_format="yaml")
        return ParsedData(data={"text": input_text}, original_format="text")

    def _parse_xml(self, xml: str, depth: int = 0) -> Any:
        if depth > 20:
            return {}
        if len(xml) > 100_000:
            xml = xml[:100_000]
        result: dict[str, Any] = {}
        xml = re.sub(r"<\?xml.*?\?>", "", xml)
        pattern = re.compile(r"<([^/>]+)>([\s\S]*?)</\1>")
        for tag_name, content in pattern.findall(xml):
            parsed: Union[str, Any]
            if "<" in content:
                parsed = self._parse_xml(content, depth + 1)
            else:
                parsed = content.strip()
            if tag_name in result:
                existing = result[tag_name]
                if not isinstance(existing, list):
                    result[tag_name] = [existing]
                result[tag_name].append(parsed)
            else:
                result[tag_name] = parsed
        return result

    def _parse_csv(self, csv_text: str) -> List[dict[str, str]]:
        lines = csv_text.strip().split("\n")
        if len(lines) < 2:
            return []
        headers = self._parse_csv_line(lines[0])
        rows: List[dict[str, str]] = []
        for line in lines[1:]:
            values = self._parse_csv_line(line)
            rows.append({headers[i]: values[i] if i < len(values) else "" for i in range(len(headers))})
        return rows

    def _parse_csv_line(self, line: str) -> List[str]:
        result: List[str] = []
        current: List[str] = []
        in_quotes = False
        i = 0
        while i < len(line):
            ch = line[i]
            if in_quotes:
                if ch == '"':
                    if i + 1 < len(line) and line[i + 1] == '"':
                        current.append('"')
                        i += 2
                        continue
                    in_quotes = False
                else:
                    current.append(ch)
            else:
                if ch == '"':
                    in_quotes = True
                elif ch == ",":
                    result.append("".join(current).strip())
                    current = []
                else:
                    current.append(ch)
            i += 1
        result.append("".join(current).strip())
        return result

    def _parse_yaml(self, yaml_text: str) -> dict[str, Any]:
        root: dict[str, Any] = {}
        stack: List[dict[str, Any]] = [root]
        indents: List[int] = [-1]
        for raw_line in yaml_text.split("\n"):
            line = raw_line.rstrip()
            if not line.strip() or line.strip().startswith("#"):
                continue
            if line.strip() == "---":
                continue
            match = re.match(r"^(\s*)([^:]+):\s*(.*)$", line)
            if not match:
                continue
            indent_str, raw_key, raw_value = match.groups()
            indent = len(indent_str)
            key = raw_key.strip()
            value = raw_value.strip()
            while len(indents) > 1 and indents[-1] >= indent:
                stack.pop()
                indents.pop()
            parent = stack[-1]
            if not value:
                parent[key] = {}
                stack.append(parent[key])
                indents.append(indent)
                continue
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            elif value == "true":
                value = True
            elif value == "false":
                value = False
            parent[key] = value
        return root

    def serialize(self, data: Any, fmt: FormatName) -> str:
        if fmt == "json":
            return json.dumps(data, indent=2)
        if fmt == "xml":
            return self._to_xml(data)
        if fmt == "csv":
            return self._to_csv(data)
        if fmt == "yaml":
            return self._to_yaml(data)
        if isinstance(data, str):
            return data
        if isinstance(data, dict) and "text" in data and len(data) == 1:
            return str(data["text"])
        return json.dumps(data, indent=2)

    def _to_xml(self, obj: Any, root_name: str = "root") -> str:
        lines = ['<?xml version="1.0" encoding="UTF-8"?>', f"<{root_name}>"]
        for key, value in obj.items():
            if isinstance(value, dict):
                lines.append(f"  <{key}>")
                lines.append(self._object_to_xml(value, 4))
                lines.append(f"  </{key}>")
            else:
                lines.append(f"  <{key}>{self._escape_xml(str(value))}</{key}>")
        lines.append(f"</{root_name}>")
        return "\n".join(lines)

    def _object_to_xml(self, obj: dict[str, Any], indent: int) -> str:
        spaces = " " * indent
        lines: List[str] = []
        for key, value in obj.items():
            if isinstance(value, dict):
                lines.append(f"{spaces}<{key}>")
                lines.append(self._object_to_xml(value, indent + 2))
                lines.append(f"{spaces}</{key}>")
            else:
                lines.append(f"{spaces}<{key}>{self._escape_xml(str(value))}</{key}>")
        return "\n".join(lines).rstrip()

    def _escape_xml(self, value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def _to_csv(self, data: Any) -> str:
        rows = data if isinstance(data, list) else [data]
        if not rows:
            return ""
        headers = [key for key in rows[0].keys() if not str(key).startswith("_")]
        lines = [",".join(self._escape_csv_field(str(header)) for header in headers)]
        for row in rows:
            values: List[str] = []
            for header in headers:
                raw = row.get(header, "")
                val = "" if raw is None else str(raw)
                val = self._neutralize_csv_formula(val)
                if re.search(r'[,\n"]', val):
                    val = f'"{val.replace(chr(34), chr(34) + chr(34))}"'
                values.append(val)
            lines.append(",".join(values))
        return "\n".join(lines)

    def _neutralize_csv_formula(self, value: str) -> str:
        if not value:
            return value
        first = ord(value[0])
        if first in (0x3D, 0x2B, 0x2D, 0x40, 0x09, 0x0D):
            return f"'{value}"
        return value

    def _escape_csv_field(self, value: str) -> str:
        val = self._neutralize_csv_formula(value)
        if re.search(r'[,\n"]', val):
            val = f'"{val.replace(chr(34), chr(34) + chr(34))}"'
        return val

    def _to_yaml(self, obj: Any, indent: int = 0) -> str:
        spaces = " " * indent
        lines: List[str] = []
        for key, value in obj.items():
            if isinstance(value, dict):
                lines.append(f"{spaces}{key}:")
                lines.append(self._to_yaml(value, indent + 2))
            elif isinstance(value, list):
                lines.append(f"{spaces}{key}: [{', '.join(str(item) for item in value)}]")
            else:
                string_value = str(value)
                needs_quotes = (
                    ":" in string_value
                    or "#" in string_value
                    or string_value.startswith(("{", "[", "&", "*", "!", "%", "@", "`", "'", '"', "|", ">"))
                    or string_value in {"null", "true", "false", "~"}
                    or string_value.strip() != string_value
                    or (string_value.isdigit() and string_value != "")
                )
                escaped = string_value.replace("\\", "\\\\").replace('"', '\\"')
                rendered = f'"{escaped}"' if needs_quotes else string_value
                lines.append(f"{spaces}{key}: {rendered}")
        return "\n".join(lines) + ("\n" if lines else "")