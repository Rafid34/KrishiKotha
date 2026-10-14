"""Inbound message parser for SMS commands and district/crop registration (Sections 7.4, 9)."""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass

DISTRICT_MAP: dict[str, str] = {
    "sylhet": "sylhet",
    "সিলেট": "sylhet",
    "sunamganj": "sunamganj",
    "সুনামগঞ্জ": "sunamganj",
    "khulna": "khulna",
    "খুলনা": "khulna",
    "satkhira": "satkhira",
    "সাতক্ষীরা": "satkhira",
    "barishal": "barishal",
    "বরিশাল": "barishal",
    "rajshahi": "rajshahi",
    "রাজশাহী": "rajshahi",
    "rangpur": "rangpur",
    "রংপুর": "rangpur",
    "chattogram": "chattogram",
    "chittagong": "chattogram",
    "চট্টগ্রাম": "chattogram",
}

CROP_MAP: dict[str, str] = {
    "aman": "aman",
    "আমন": "aman",
    "boro": "boro",
    "বোরো": "boro",
    "aus": "aus",
    "আউশ": "aus",
}

COMMANDS_HELP = {"help", "সাহায্য"}
COMMANDS_STOP = {"stop", "বন্ধ"}
FEEDBACK_1 = {"1", "১"}
FEEDBACK_2 = {"2", "২"}


@dataclass(frozen=True)
class ParsedMessage:
    """Structured representation of parsed inbound SMS text."""

    command: str  # "register", "help", "stop", "feedback", "unknown"
    district_id: str | None = None
    crop_id: str | None = None
    feedback_value: int | None = None
    raw_text: str = ""


def parse_message(raw_text: str | None) -> ParsedMessage:
    """Parse inbound SMS text with case and whitespace tolerance and NFC normalization.

    Recognises:
        - '<DISTRICT> <CROP>' in English or Bangla -> command='register'
        - 'HELP' / 'সাহায্য' -> command='help'
        - 'STOP' / 'বন্ধ' -> command='stop'
        - '1' / '১', '2' / '২' -> command='feedback'
        - anything else -> command='unknown'
    """
    if not raw_text:
        return ParsedMessage(command="unknown", raw_text="")

    # Unicode normalization (NFC)
    normalized = unicodedata.normalize("NFC", raw_text.strip())
    lower_text = normalized.lower()

    if not lower_text:
        return ParsedMessage(command="unknown", raw_text=raw_text)

    # Command matches
    if lower_text in COMMANDS_HELP:
        return ParsedMessage(command="help", raw_text=raw_text)
    if lower_text in COMMANDS_STOP:
        return ParsedMessage(command="stop", raw_text=raw_text)
    if lower_text in FEEDBACK_1:
        return ParsedMessage(command="feedback", feedback_value=1, raw_text=raw_text)
    if lower_text in FEEDBACK_2:
        return ParsedMessage(command="feedback", feedback_value=2, raw_text=raw_text)

    # Clean tokens: ignore common filler words like "ধান" (rice)
    raw_tokens = lower_text.split()
    tokens = [t for t in raw_tokens if t not in ("ধান", "rice")]

    found_district: str | None = None
    found_crop: str | None = None

    for token in tokens:
        if token in DISTRICT_MAP and found_district is None:
            found_district = DISTRICT_MAP[token]
        elif token in CROP_MAP and found_crop is None:
            found_crop = CROP_MAP[token]

    if found_district and found_crop:
        return ParsedMessage(
            command="register",
            district_id=found_district,
            crop_id=found_crop,
            raw_text=raw_text,
        )

    return ParsedMessage(command="unknown", raw_text=raw_text)
