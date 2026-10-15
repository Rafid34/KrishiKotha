"""Backtest and event replay calculation (Section 8.4, 9 task 8.4).

Derives replay step dates and lead time directly from data without hard-coded
dates or tuned thresholds.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from .risk.scoring import level_for

REFERENCE_ONSET_DEFAULT = date(2022, 6, 16)
REFERENCE_ONSET_CITATION = (
    "Flood Forecasting and Warning Centre (FFWC), Bangladesh Water Development Board (BWDB), "
    "'Annual Flood Report 2022' & UN OCHA / ReliefWeb 'Bangladesh: Floods - Jun 2022': "
    "Surma-Kushiyara river basin crossed danger level with catastrophic inundation of Sylhet on 16 June 2022."
)

STEP_LABELS: dict[int, dict[str, str]] = {
    1: {"en": "Rain begins", "bn": "বৃষ্টি শুরু"},
    2: {"en": "Rain builds", "bn": "বৃষ্টি বাড়ছে"},
    3: {"en": "Heavy rain", "bn": "ভারী বৃষ্টি"},
    4: {"en": "Extreme rain", "bn": "অতি ভারী বৃষ্টি"},
    5: {"en": "Flood", "bn": "বন্যা"},
}


def _extract_point_data(point: Any) -> dict[str, Any]:
    """Extract standard backtest fields from a RiskSnapshot object or dict."""
    if isinstance(point, dict):
        d_val = point["date"]
        date_obj = date.fromisoformat(d_val) if isinstance(d_val, str) else d_val
        fs = float(point.get("flood_score", 0.0))
        fl = point.get("flood_level") or level_for(fs)
        inputs = point.get("inputs") or {}
        r3_pctl = None
        r7_pctl = None
        if isinstance(inputs, dict) and "flood" in inputs and isinstance(inputs["flood"], dict):
            for inp in inputs["flood"].get("inputs", []):
                if inp.get("name") == "rain3_pctl":
                    r3_pctl = inp.get("value")
                elif inp.get("name") == "rain7_pctl":
                    r7_pctl = inp.get("value")
        if r3_pctl is None:
            r3_pctl = point.get("rain3_pctl", point.get("f_rain3"))
        if r7_pctl is None:
            r7_pctl = point.get("rain7_pctl", point.get("f_rain7"))
        return {
            "date": date_obj,
            "flood_score": fs,
            "flood_level": fl,
            "rain3_pctl": float(r3_pctl) if r3_pctl is not None else None,
            "rain7_pctl": float(r7_pctl) if r7_pctl is not None else None,
            "rain_mm": point.get("rain_mm"),
            "soil_wetness": point.get("soil_wetness"),
            "rain_pctl_90": point.get("rain_pctl_90"),
        }
    else:
        # RiskSnapshot ORM model
        date_obj = point.date
        fs = float(point.flood_score)
        fl = point.flood_level or level_for(fs)
        r3_pctl = None
        r7_pctl = None
        inputs = point.inputs or {}
        if isinstance(inputs, dict) and "flood" in inputs and isinstance(inputs["flood"], dict):
            for inp in inputs["flood"].get("inputs", []):
                if inp.get("name") == "rain3_pctl":
                    r3_pctl = inp.get("value")
                elif inp.get("name") == "rain7_pctl":
                    r7_pctl = inp.get("value")
        return {
            "date": date_obj,
            "flood_score": fs,
            "flood_level": fl,
            "rain3_pctl": float(r3_pctl) if r3_pctl is not None else None,
            "rain7_pctl": float(r7_pctl) if r7_pctl is not None else None,
            "rain_mm": None,
            "soil_wetness": None,
            "rain_pctl_90": None,
        }


def compute_backtest(
    series: list[Any],
    reference_onset: date | str = REFERENCE_ONSET_DEFAULT,
) -> dict[str, Any]:
    """Compute replay steps, lead time and flood milestones from a snapshot series.

    Rules from Task 8.4:
    - step 1: first day rainfall exceeds the 50th baseline percentile of the 3-day sum (rain3_pctl > 50)
    - step 2: first day f_rain7 is at least 60 (rain7_pctl >= 60)
    - step 3: first day flood level is Moderate or High (flood_level in ('moderate', 'high'))
    - step 4: first day flood level is High (flood_level == 'high')
    - step 5: reference onset date
    """
    if isinstance(reference_onset, str):
        ref_date = date.fromisoformat(reference_onset)
    else:
        ref_date = reference_onset

    parsed = [_extract_point_data(p) for p in series]
    parsed.sort(key=lambda x: x["date"])

    step1_date: date | None = None
    step2_date: date | None = None
    step3_date: date | None = None
    step4_date: date | None = None

    # Step 1: first day rainfall exceeds the 50th baseline percentile of the 3-day sum
    for p in parsed:
        if p["rain3_pctl"] is not None and p["rain3_pctl"] > 50.0:
            step1_date = p["date"]
            break

    # Step 2: first day f_rain7 is at least 60 (on or after Step 1)
    for p in parsed:
        if step1_date is not None and p["date"] < step1_date:
            continue
        if p["rain7_pctl"] is not None and p["rain7_pctl"] >= 60.0:
            step2_date = p["date"]
            break

    # Step 3: first day flood level is Moderate or High (on or after Step 2)
    for p in parsed:
        if step2_date is not None and p["date"] < step2_date:
            continue
        if p["flood_level"] in ("moderate", "high"):
            step3_date = p["date"]
            break

    # Step 4: first day flood level is High (on or after Step 3)
    for p in parsed:
        if step3_date is not None and p["date"] < step3_date:
            continue
        if p["flood_level"] == "high":
            step4_date = p["date"]
            break

    first_mod_str = step3_date.isoformat() if step3_date else None
    first_high_str = step4_date.isoformat() if step4_date else None

    lead_time: int | None = None
    if step4_date is not None:
        lead_time = (ref_date - step4_date).days

    steps = [
        {
            "step": 1,
            "label": STEP_LABELS[1]["en"],
            "label_bn": STEP_LABELS[1]["bn"],
            "date": step1_date.isoformat() if step1_date else None,
        },
        {
            "step": 2,
            "label": STEP_LABELS[2]["en"],
            "label_bn": STEP_LABELS[2]["bn"],
            "date": step2_date.isoformat() if step2_date else None,
        },
        {
            "step": 3,
            "label": STEP_LABELS[3]["en"],
            "label_bn": STEP_LABELS[3]["bn"],
            "date": first_mod_str,
        },
        {
            "step": 4,
            "label": STEP_LABELS[4]["en"],
            "label_bn": STEP_LABELS[4]["bn"],
            "date": first_high_str,
        },
        {
            "step": 5,
            "label": STEP_LABELS[5]["en"],
            "label_bn": STEP_LABELS[5]["bn"],
            "date": ref_date.isoformat(),
        },
    ]

    formatted_series = [
        {
            "date": p["date"].isoformat(),
            "flood_score": round(p["flood_score"], 2),
            "flood_level": p["flood_level"],
            "rain_mm": round(p["rain_mm"], 2) if p["rain_mm"] is not None else None,
            "soil_wetness": round(p["soil_wetness"], 4) if p["soil_wetness"] is not None else None,
            "rain_pctl_90": round(p["rain_pctl_90"], 2) if p["rain_pctl_90"] is not None else None,
        }
        for p in parsed
    ]

    return {
        "district_id": "sylhet",
        "series": formatted_series,
        "first_moderate": first_mod_str,
        "first_high": first_high_str,
        "reference_onset": ref_date.isoformat(),
        "lead_time_days": lead_time,
        "steps": steps,
        "citation": REFERENCE_ONSET_CITATION,
    }
