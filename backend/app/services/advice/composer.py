"""Loads advice templates, fills placeholders, normalises Unicode (NFC), and enforces length limits (Sections 7.4, 9)."""
from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from typing import Any

from ...config import STATIC_DIR

MAX_BANGLA_SMS_CHARS = 134


class MessageLengthExceededError(ValueError):
    """Raised when a composed Bangla SMS message exceeds the 134-character limit."""


@dataclass(frozen=True)
class ComposedAdvice:
    """Composed advice message in Bangla and English."""

    rule_id: str
    condition: str
    text_bn: str
    text_en: str


_TEMPLATES_CACHE: dict[str, dict[str, str]] | None = None


def load_templates() -> dict[str, dict[str, str]]:
    """Load advice templates from static configuration."""
    global _TEMPLATES_CACHE
    if _TEMPLATES_CACHE is None:
        templates_path = STATIC_DIR / "advice_templates.json"
        with open(templates_path, "r", encoding="utf-8") as f:
            _TEMPLATES_CACHE = json.load(f)
    return _TEMPLATES_CACHE


def compose_advice(rule_id: str, context: dict[str, Any] | None = None) -> ComposedAdvice:
    """Load template for rule_id, fill placeholders if any, normalise to NFC, and check length.

    Raises:
        KeyError: If rule_id is not in advice_templates.json.
        MessageLengthExceededError: If rendered text_bn exceeds 134 characters.
    """
    templates = load_templates()
    if rule_id not in templates:
        raise KeyError(f"Template rule_id '{rule_id}' not found in advice_templates.json")

    tmpl = templates[rule_id]
    condition = tmpl.get("condition", "")
    text_bn = tmpl.get("text_bn", "")
    text_en = tmpl.get("text_en", "")

    if context:
        # Fill placeholders safely
        try:
            text_bn = text_bn.format(**context)
        except KeyError:
            pass
        try:
            text_en = text_en.format(**context)
        except KeyError:
            pass

    # Normalise Unicode to NFC
    text_bn = unicodedata.normalize("NFC", text_bn)
    text_en = unicodedata.normalize("NFC", text_en)

    # Enforce strict 134-character limit on Bangla text
    if len(text_bn) > MAX_BANGLA_SMS_CHARS:
        raise MessageLengthExceededError(
            f"Rule '{rule_id}' rendered text_bn of {len(text_bn)} characters, "
            f"exceeding the {MAX_BANGLA_SMS_CHARS} limit: '{text_bn}'"
        )

    return ComposedAdvice(
        rule_id=rule_id,
        condition=condition,
        text_bn=text_bn,
        text_en=text_en,
    )
