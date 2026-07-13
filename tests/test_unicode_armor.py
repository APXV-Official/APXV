"""Tests for APX unicode armor."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.redaction.unicode_armor import detect_unicode_spoofing, unicode_armor


def test_strips_zero_width_characters():
    spoofed = "john\u200b.doe@example.com"
    assert detect_unicode_spoofing(spoofed) is True
    assert "\u200b" not in unicode_armor(spoofed)


def test_normalizes_fullwidth_characters():
    assert unicode_armor("ＡＰＸ") == "APX"