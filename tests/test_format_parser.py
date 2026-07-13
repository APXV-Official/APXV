"""Tests for APX format parser."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.redaction.format_parser import FormatParser


def test_detects_json():
    parser = FormatParser()
    assert parser.detect_format('{"name":"Alice","age":30}') == "json"


def test_detects_csv():
    parser = FormatParser()
    csv = "name,email,phone\nAlice,alice@example.com,555-1234\nBob,bob@example.com,555-5678\nCarol,carol@example.com,555-9012"
    assert parser.detect_format(csv) == "csv"


def test_detects_plain_text():
    parser = FormatParser()
    assert parser.detect_format("Hello world, this is a sentence.") == "text"


def test_oversized_input_short_circuits_to_text():
    parser = FormatParser()
    huge = "{" + '"a":1,' * 99_999 + '"a":1}'
    assert len(huge) > 500_000
    assert parser.detect_format(huge) == "text"