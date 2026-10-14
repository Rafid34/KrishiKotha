"""Tests for advice engine, templates, rules, and character limits (Sections 7.4, 7.5, 9)."""
from __future__ import annotations

import json
import unicodedata
from datetime import date
from unittest.mock import patch

import pytest

from backend.app.config import STATIC_DIR
from backend.app.services.advice.composer import (
    MAX_BANGLA_SMS_CHARS,
    MessageLengthExceededError,
    compose_advice,
    load_templates,
)
from backend.app.services.advice.rules import select_advice_rule
from backend.app.services.advice.stages import get_crop_stage

# The 8 districts from Section 7.5
DISTRICT_IDS = [
    "sylhet",
    "sunamganj",
    "khulna",
    "satkhira",
    "barishal",
    "rajshahi",
    "rangpur",
    "chattogram",
]

# The 3 crops from Section 7.5
CROP_IDS = ["aman", "boro", "aus"]

# Verbatim Section 7.4 templates
SPEC_TEMPLATES = {
    "drought_high_transplant": {
        "text_bn": "আপনার জমির মাটি খুব শুকনো। আমন ধান রোপণের আগে ৫ দিন অপেক্ষা করুন।",
        "text_en": "Your soil is very dry. Wait 5 days before transplanting Aman rice.",
    },
    "drought_moderate_any": {
        "text_bn": "মাটির আর্দ্রতা কমছে। সম্ভব হলে ভোরে বা সন্ধ্যায় হালকা সেচ দিন।",
        "text_en": "Soil moisture is falling. If possible, give light irrigation at dawn or dusk.",
    },
    "flood_high_harvest": {
        "text_bn": "গত কয়েক দিনে অনেক বৃষ্টি হয়েছে, বন্যার ঝুঁকি বাড়ছে। সম্ভব হলে আগেই ধান কেটে ফেলুন।",
        "text_en": "Heavy rain has fallen in recent days and flood risk is rising. If possible, harvest the rice early.",
    },
    "flood_high_early": {
        "text_bn": "বন্যার ঝুঁকি বেশি। জমির পানি বের করার নালা পরিষ্কার রাখুন এবং বীজতলা উঁচু স্থানে রাখুন।",
        "text_en": "Flood risk is high. Keep drainage channels clear and keep seedbeds on high ground.",
    },
    "flood_moderate_any": {
        "text_bn": "এই এলাকায় বৃষ্টি বাড়ছে। জমির পানি বের করার নালা পরিষ্কার রাখুন।",
        "text_en": "Rain is increasing in your area. Keep field drainage channels clear.",
    },
    "salt_high_any": {
        "text_bn": "আপনার এলাকায় লবণাক্ততার ঝুঁকি বেশি। সেচের আগে পানি পরীক্ষা করুন এবং সম্ভব হলে মিঠা পানি ব্যবহার করুন।",
        "text_en": "Salinity risk is high in your area. Test water before irrigation and use fresh water if possible.",
    },
    "none_low": {
        "text_bn": "এখন বড় কোনো ঝুঁকি নেই। স্বাভাবিকভাবে চাষ চালিয়ে যান।",
        "text_en": "No major risk right now. Continue farming as normal.",
    },
    "welcome": {
        "text_bn": "কৃষি কথায় স্বাগতম। আপনার এলাকা ও ফসল নথিভুক্ত হয়েছে। আমরা সতর্কবার্তা পাঠাব।",
        "text_en": "Welcome to Krishi Kotha. Your area and crop are registered. We will send you alerts.",
    },
    "help": {
        "text_bn": "বুঝতে পারিনি। এভাবে লিখুন: SYLHET AMAN",
        "text_en": "We did not understand. Write like this: SYLHET AMAN",
    },
    "stopped": {
        "text_bn": "আপনার সাবস্ক্রিপশন বন্ধ হয়েছে।",
        "text_en": "Your subscription has been stopped.",
    },
}


def test_verbatim_templates_from_spec():
    """Verify that templates in advice_templates.json match Section 7.4 verbatim."""
    templates = load_templates()
    for rule_id, expected in SPEC_TEMPLATES.items():
        assert rule_id in templates, f"Missing template '{rule_id}'"
        actual_bn = unicodedata.normalize("NFC", templates[rule_id]["text_bn"])
        expected_bn = unicodedata.normalize("NFC", expected["text_bn"])
        assert actual_bn == expected_bn, f"Bangla text mismatch for rule '{rule_id}'"

        actual_en = unicodedata.normalize("NFC", templates[rule_id]["text_en"])
        expected_en = unicodedata.normalize("NFC", expected["text_en"])
        assert actual_en == expected_en, f"English text mismatch for rule '{rule_id}'"


def test_bangla_length_limit_all_templates():
    """Verify that every template in advice_templates.json is at most 134 characters (two SMS segments)."""
    templates = load_templates()
    for rule_id, entry in templates.items():
        text_bn = unicodedata.normalize("NFC", entry["text_bn"])
        length = len(text_bn)
        assert length <= MAX_BANGLA_SMS_CHARS, (
            f"Template '{rule_id}' has {length} characters, exceeding {MAX_BANGLA_SMS_CHARS}: '{text_bn}'"
        )


def test_134_char_limit_enforced_by_composer():
    """Verify that composer strictly raises MessageLengthExceededError when text_bn exceeds 134 chars."""
    over_limit_text = "ক" * 135
    fake_templates = {
        "test_overflow": {
            "condition": "test",
            "text_bn": over_limit_text,
            "text_en": "Test overflow message",
        }
    }

    with patch("backend.app.services.advice.composer.load_templates", return_value=fake_templates):
        with pytest.raises(MessageLengthExceededError) as exc_info:
            compose_advice("test_overflow")
        assert "exceeding the 134 limit" in str(exc_info.value)


def test_messages_describe_observed_conditions_only_never_forecasts():
    """Section 7.4 & prompt: Level 1 and 2 messages describe observed conditions only, never forecasts.

    Messages must not claim a forecast ('next week', 'forecast', 'আগামী সপ্তাহ', 'পূর্বাভাস').
    """
    templates = load_templates()
    forbidden_terms = ["next week", "forecast", "coming week", "আগামী সপ্তাহ", "পূর্বাভাস", "সামনের সপ্তাহ"]

    for rule_id, entry in templates.items():
        bn = entry.get("text_bn", "").lower()
        en = entry.get("text_en", "").lower()
        for term in forbidden_terms:
            assert term not in bn, f"Rule '{rule_id}' contains forecast term '{term}' in text_bn"
            assert term not in en, f"Rule '{rule_id}' contains forecast term '{term}' in text_en"


@pytest.mark.parametrize("district_id", DISTRICT_IDS)
@pytest.mark.parametrize("crop_id", CROP_IDS)
def test_all_templates_render_for_8_districts_by_3_crops(district_id: str, crop_id: str):
    """Parametrized test: all templates render without unresolved placeholders for all 8 districts and 3 crops."""
    # Test rendering of all rule templates with district and crop context
    context = {"district": district_id, "crop": crop_id}
    templates = load_templates()

    for rule_id in templates:
        advice = compose_advice(rule_id, context=context)
        # Ensure no unresolved placeholders
        assert "{" not in advice.text_bn and "}" not in advice.text_bn, (
            f"Unresolved placeholder in text_bn for rule '{rule_id}'"
        )
        assert "{" not in advice.text_en and "}" not in advice.text_en, (
            f"Unresolved placeholder in text_en for rule '{rule_id}'"
        )
        assert len(advice.text_bn) <= MAX_BANGLA_SMS_CHARS


def test_rule_selection_order_and_priorities():
    """Rule selection order: evaluate in order flood, drought, salt; highest effective value >= 40 wins."""
    sensitivities = {"flood": 1.0, "drought": 1.0, "salt": 1.0}

    # 1. Flood wins on tie with drought (flood evaluated first)
    res = select_advice_rule(
        flood_score=75.0,
        drought_score=75.0,
        salt_score=10.0,
        crop_id="aman",
        stage_key="vegetative",
        sensitivities=sensitivities,
    )
    assert res.hazard == "flood"
    assert res.rule_id == "flood_high_early"

    # 2. Drought wins on tie with salt
    res = select_advice_rule(
        flood_score=20.0,
        drought_score=55.0,
        salt_score=55.0,
        crop_id="aman",
        stage_key="vegetative",
        sensitivities=sensitivities,
    )
    assert res.hazard == "drought"
    assert res.rule_id == "drought_moderate_any"

    # 3. Higher effective value wins regardless of evaluation order
    res = select_advice_rule(
        flood_score=45.0,
        drought_score=85.0,
        salt_score=10.0,
        crop_id="aman",
        stage_key="nursery",
        sensitivities=sensitivities,
    )
    assert res.hazard == "drought"
    assert res.rule_id == "drought_high_transplant"

    # 4. No hazard at or above 40 returns 'none_low'
    res = select_advice_rule(
        flood_score=39.9,
        drought_score=39.9,
        salt_score=39.9,
        crop_id="aman",
        stage_key="vegetative",
        sensitivities=sensitivities,
    )
    assert res.hazard is None
    assert res.rule_id == "none_low"
    assert res.level == "low"


def test_flood_rule_conditions():
    """Verify flood rule branches: high-harvest, high-early, moderate-any."""
    sens = {"flood": 1.0, "drought": 0.5, "salt": 0.5}

    # High flood with grain_filling_harvest
    res = select_advice_rule(80.0, 10.0, 10.0, "aman", "grain_filling_harvest", sens)
    assert res.rule_id == "flood_high_harvest"
    assert res.level == "high"

    # High flood with early stage (nursery)
    res = select_advice_rule(80.0, 10.0, 10.0, "aman", "nursery", sens)
    assert res.rule_id == "flood_high_early"
    assert res.level == "high"

    # Moderate flood (score 55)
    res = select_advice_rule(55.0, 10.0, 10.0, "aman", "nursery", sens)
    assert res.rule_id == "flood_moderate_any"
    assert res.level == "moderate"


def test_drought_rule_conditions():
    """Verify drought rule branches: high-transplant for Aman nursery/transplanting, moderate for other."""
    sens = {"flood": 0.5, "drought": 1.0, "salt": 0.5}

    # High drought + Aman + nursery -> drought_high_transplant
    res = select_advice_rule(10.0, 75.0, 10.0, "aman", "nursery", sens)
    assert res.rule_id == "drought_high_transplant"

    # High drought + Aman + transplanting -> drought_high_transplant
    res = select_advice_rule(10.0, 75.0, 10.0, "aman", "transplanting", sens)
    assert res.rule_id == "drought_high_transplant"

    # High drought + Aman + vegetative -> drought_moderate_any
    res = select_advice_rule(10.0, 75.0, 10.0, "aman", "vegetative", sens)
    assert res.rule_id == "drought_moderate_any"

    # High drought + Boro + vegetative -> drought_moderate_any
    res = select_advice_rule(10.0, 75.0, 10.0, "boro", "vegetative", sens)
    assert res.rule_id == "drought_moderate_any"

    # Moderate drought (score 50) -> drought_moderate_any
    res = select_advice_rule(10.0, 50.0, 10.0, "aman", "nursery", sens)
    assert res.rule_id == "drought_moderate_any"


def test_salt_rule_conditions():
    """Verify salt rule: salt_high_any for any high or moderate salinity."""
    sens = {"flood": 0.5, "drought": 0.5, "salt": 1.0}

    # High salt
    res = select_advice_rule(10.0, 10.0, 75.0, "khulna", "vegetative", sens)
    assert res.rule_id == "salt_high_any"

    # Moderate salt
    res = select_advice_rule(10.0, 10.0, 45.0, "satkhira", "vegetative", sens)
    assert res.rule_id == "salt_high_any"


def test_crop_stages_mapping_overlap_and_offseason():
    """Verify stage mapping, overlapping month rule (later stage wins), and off_season fallback."""
    # Aman: nursery (Jun-Jul), transplanting (Jul-Aug)
    # Month 6 (June) -> nursery
    stage_jun = get_crop_stage("aman", date(2022, 6, 15))
    assert stage_jun.stage_key == "nursery"
    assert stage_jun.is_off_season is False

    # Month 7 (July) -> transplanting wins over nursery (methodology.md)
    stage_jul = get_crop_stage("aman", date(2022, 7, 15))
    assert stage_jul.stage_key == "transplanting"

    # Month 8 (August) -> vegetative wins over transplanting
    stage_aug = get_crop_stage("aman", date(2022, 8, 15))
    assert stage_aug.stage_key == "vegetative"

    # Off-season for Aman in March (month 3)
    stage_mar = get_crop_stage("aman", date(2022, 3, 15))
    assert stage_mar.stage_key == "off_season"
    assert stage_mar.is_off_season is True
    assert stage_mar.sensitivities == {"flood": 0.7, "drought": 0.7, "salt": 0.7}

    # Wrap-around: Boro transplanting is Dec to Jan (12 to 1), vegetative is Jan to Feb (1 to 2)
    # In January (month 1), vegetative wins over transplanting
    stage_boro_jan = get_crop_stage("boro", date(2022, 1, 15))
    assert stage_boro_jan.stage_key == "vegetative"
