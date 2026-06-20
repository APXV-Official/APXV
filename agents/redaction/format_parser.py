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