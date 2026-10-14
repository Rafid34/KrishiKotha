"""Tests for inbound SMS parsing (English, Bangla, whitespace, commands) (Sections 7.4, 9)."""
from __future__ import annotations

import pytest

from backend.app.services.messaging.parser import parse_message


@pytest.mark.parametrize(
    "raw_input, expected_district, expected_crop",
    [
        ("SYLHET AMAN", "sylhet", "aman"),
        ("sylhet aman", "sylhet", "aman"),
        ("সিলেট আমন", "sylhet", "aman"),
        ("  KHULNA   BORO  ", "khulna", "boro"),
        ("খুলনা বোরো", "khulna", "boro"),
        ("RAJSHAHI AUS", "rajshahi", "aus"),
        ("রাজশাহী আউশ", "rajshahi", "aus"),
        ("satkhira aman", "satkhira", "aman"),
        ("সাতক্ষীরা আমন", "satkhira", "aman"),
        ("BARISHAL BORO", "barishal", "boro"),
        ("বরিশাল বোরো ধান", "barishal", "boro"),
        ("rangpur aus", "rangpur", "aus"),
        ("রংপুর আউশ", "rangpur", "aus"),
        ("chattogram aman", "chattogram", "aman"),
        ("চট্টগ্রাম আমন", "chattogram", "aman"),
        ("sunamganj boro", "sunamganj", "boro"),
        ("সুনামগঞ্জ আমন ধান", "sunamganj", "aman"),
    ],
)
def test_parse_district_and_crop(raw_input: str, expected_district: str, expected_crop: str):
    """Test English and Bangla district and crop parsing with whitespace and case tolerance."""
    res = parse_message(raw_input)
    assert res.command == "register"
    assert res.district_id == expected_district
    assert res.crop_id == expected_crop


@pytest.mark.parametrize(
    "cmd_input, expected_cmd",
    [
        ("HELP", "help"),
        ("help", "help"),
        ("Help", "help"),
        ("সাহায্য", "help"),
        ("STOP", "stop"),
        ("stop", "stop"),
        ("Stop", "stop"),
        ("বন্ধ", "stop"),
    ],
)
def test_parse_standard_commands(cmd_input: str, expected_cmd: str):
    """Test HELP and STOP commands in English and Bangla."""
    res = parse_message(cmd_input)
    assert res.command == expected_cmd


@pytest.mark.parametrize(
    "feedback_input, expected_val",
    [
        ("1", 1),
        ("১", 1),
        ("2", 2),
        ("২", 2),
    ],
)
def test_parse_feedback_commands(feedback_input: str, expected_val: int):
    """Test feedback command parsing for Level 3 measurement loop."""
    res = parse_message(feedback_input)
    assert res.command == "feedback"
    assert res.feedback_value == expected_val


@pytest.mark.parametrize(
    "invalid_input",
    [
        "",
        "   ",
        "RANDOM TEXT",
        "HELLO WORLD",
        "SYLHET",  # missing crop
        "AMAN",  # missing district
        "UNKNOWN AMAN",
        "SYLHET UNKNOWN",
        "12345",
    ],
)
def test_parse_invalid_inputs(invalid_input: str):
    """Invalid input should return unknown command (which triggers help message in handler)."""
    res = parse_message(invalid_input)
    assert res.command == "unknown"
    assert res.district_id is None
    assert res.crop_id is None
