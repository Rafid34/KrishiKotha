"""Maps date and crop to growth stage and sensitivities (Sections 7.4, 7.5)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from ...config import STATIC_DIR


@dataclass(frozen=True)
class CropStage:
    """Growth stage and hazard sensitivities for a crop on a specific date."""

    crop_id: str
    stage_key: str
    sensitivities: dict[str, float]
    is_off_season: bool = False


_CROPS_CACHE: dict[str, Any] | None = None


def _load_crops_data() -> dict[str, Any]:
    global _CROPS_CACHE
    if _CROPS_CACHE is None:
        crops_file = STATIC_DIR / "crops.json"
        with open(crops_file, "r", encoding="utf-8") as f:
            _CROPS_CACHE = json.load(f)
    return _CROPS_CACHE


def _month_in_range(month: int, start: int, end: int) -> bool:
    """Check if month is within start and end month (inclusive, wrap-around allowed)."""
    if start <= end:
        return start <= month <= end
    return month >= start or month <= end


def get_crop_stage(crop_id: str, target_date: date | datetime | str) -> CropStage:
    """Determine crop growth stage and hazard sensitivities for a given date.

    Where two stages overlap in a month (e.g. Aman Jul is both nursery and
    transplanting), the later stage in crops.json order wins (docs/methodology.md).
    If the date falls outside every stage, stage is 'off_season' with sensitivities 0.7.
    """
    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)
    elif isinstance(target_date, datetime):
        target_date = target_date.date()

    month = target_date.month
    data = _load_crops_data()
    crop_norm = crop_id.strip().lower()

    crop_entry = None
    for c in data.get("crops", []):
        if c["id"].lower() == crop_norm:
            crop_entry = c
            break

    if not crop_entry:
        raise ValueError(f"Unknown crop: '{crop_id}'")

    matched_stage: dict[str, Any] | None = None
    for stage in crop_entry.get("stages", []):
        start = stage["start_month"]
        end = stage["end_month"]
        if _month_in_range(month, start, end):
            # Later stage in crops.json order wins on overlap
            matched_stage = stage

    if matched_stage is not None:
        return CropStage(
            crop_id=crop_norm,
            stage_key=matched_stage["key"],
            sensitivities={
                "flood": float(matched_stage["flood"]),
                "drought": float(matched_stage["drought"]),
                "salt": float(matched_stage["salt"]),
            },
            is_off_season=False,
        )

    off_season_sens = data.get("off_season", {"flood": 0.7, "drought": 0.7, "salt": 0.7})
    return CropStage(
        crop_id=crop_norm,
        stage_key="off_season",
        sensitivities={
            "flood": float(off_season_sens.get("flood", 0.7)),
            "drought": float(off_season_sens.get("drought", 0.7)),
            "salt": float(off_season_sens.get("salt", 0.7)),
        },
        is_off_season=True,
    )
