"""Full port of legacy format-parser unit tests."""

import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.redaction.format_parser import FormatParser

PARSER = FormatParser()


def test_detects_json_object():
    assert PARSER.detect_format('{"name":"Alice","age":30}') == "json"


def test_detects_json_array():
    assert PARSER.detect_format("[1,2,3]") == "json"


def test_invalid_json_braces_not_json():
    assert PARSER.detect_format("{bad json") != "json"


def test_detects_xml():
    assert PARSER.detect_format("<Patient><id>123</id></Patient>") == "xml"


def test_detects_csv_consistent_commas():
    csv = "name,email,phone\nAlice,alice@example.com,555-1234\nBob,bob@example.com,555-5678\nCarol,carol@example.com,555-9012"
    assert PARSER.detect_format(csv) == "csv"


def test_multiline_json_not_csv():
    assert PARSER.detect_format('{"a":1,"b":2}\n{"a":3,"b":4}') != "csv"


def test_detects_plain_text():
    assert PARSER.detect_format("Hello world, this is a sentence.") == "text"


def test_detects_yaml():
    yaml = "name: Alice\nage: 30\nemail: alice@example.com"
    assert PARSER.detect_format(yaml) == "yaml"


def test_oversized_input_short_circuits_to_text():
    huge = "{" + '"a":1,' * 99_999 + '"a":1}'
    assert len(huge) > 500_000
    start = time.time()
    assert PARSER.detect_format(huge) == "text"
    assert time.time() - start < 0.05


def test_parse_json_sets_original_format():
    result = PARSER.parse('{"x":1}')
    assert result.original_format == "json"
    assert result.data == {"x": 1}


def test_parse_xml_sets_original_format():
    result = PARSER.parse("<root><id>1</id></root>")
    assert result.original_format == "xml"


def test_parse_csv_returns_array():
    csv = "name,email\nAlice,alice@a.com\nBob,bob@b.com\nCarol,carol@c.com"
    result = PARSER.parse(csv)
    assert result.original_format == "csv"
    assert isinstance(result.data, list)
    assert len(result.data) > 0


def test_parse_text_wraps_in_text_object():
    result = PARSER.parse("just a string")
    assert result.original_format == "text"
    assert result.data["text"] == "just a string"


def test_parse_empty_string_does_not_throw():
    PARSER.parse("")


def test_serialize_json_round_trip():
    original = {"name": "Alice", "age": 30}
    serialized = PARSER.serialize(original, "json")
    assert json.loads(serialized) == original


def test_serialize_csv_contains_rows():
    rows = [
        {"name": "Alice", "email": "alice@example.com"},
        {"name": "Bob", "email": "bob@example.com"},
    ]
    csv = PARSER.serialize(rows, "csv")
    assert "name" in csv
    assert "email" in csv
    assert "Alice" in csv
    assert "Bob" in csv


def test_serialize_yaml_contains_keys():
    data = {"firstName": "Jane", "role": "doctor", "active": "true"}
    yaml = PARSER.serialize(data, "yaml")
    assert "firstName" in yaml
    assert "Jane" in yaml
    assert "role" in yaml


def test_serialize_xml_contains_tags():
    data = {"patientId": "123", "name": "John"}
    xml = PARSER.serialize(data, "xml")
    assert "<patientId>" in xml
    assert "123" in xml
    assert "<name>" in xml


def test_serialize_text_returns_string():
    result = PARSER.serialize({"text": "plain text here"}, "text")
    assert isinstance(result, str)
    assert result == "plain text here"


def test_csv_quotes_comma_values():
    rows = [{"description": "hello, world", "id": "1"}]
    csv = PARSER.serialize(rows, "csv")
    assert '"hello, world"' in csv


def test_csv_neutralizes_formula_values():
    rows = [
        {"col": '=cmd|"/c calc"!A1'},
        {"col": "+1+1"},
        {"col": "-2+3"},
        {"col": "@SUM(A1:A9)"},
        {"col": "\t=danger"},
        {"col": "\r=danger"},
    ]
    csv = PARSER.serialize(rows, "csv")
    for line in csv.split("\n")[1:]:
        first_char = line[1] if line.startswith('"') else line[0]
        assert first_char not in {"=", "+", "-", "@", "\t", "\r"}


def test_csv_neutralizes_formula_headers():
    rows = [{"=evil": "val", "+plus": "val"}]
    csv = PARSER.serialize(rows, "csv")
    header = csv.split("\n")[0]
    assert not header.startswith("=")
    assert "'=evil" in header
    assert "'+plus" in header


def test_hl7_detected_as_text():
    hl7 = "\r".join(
        [
            "MSH|^~\\&|SendingApp|SendingFacility|ReceivingApp|ReceivingFacility|20260304120000||ADT^A01|12345|P|2.5",
            "PID|1||123456^^^MRN||Doe^John||19800101|M",
        ]
    )
    assert PARSER.detect_format(hl7) == "text"


def test_hl7_parse_does_not_throw():
    hl7 = "MSH|^~\\&|App|Fac|App2|Fac2|20260304||ORU^R01|99|P|2.5\rPID|1||7890^^^MRN"
    PARSER.parse(hl7)


def test_hl7_parse_original_format_text():
    hl7 = "MSH|^~\\&|X|Y|A|B|20260304||ADT^A01|1|P|2.5"
    assert PARSER.parse(hl7).original_format == "text"


def test_deep_xml_does_not_throw():
    open_tags = "".join(f"<l{i}>" for i in range(100))
    close_tags = "".join(f"</l{99 - i}>" for i in range(100))
    PARSER.parse(f"{open_tags}value{close_tags}")


def test_large_xml_completes_quickly():
    chunk = "<item><a>hello</a></item>" * 8000
    xml = f"<root>{chunk}</root>"
    start = time.time()
    PARSER.parse(xml)
    assert time.time() - start < 5.0