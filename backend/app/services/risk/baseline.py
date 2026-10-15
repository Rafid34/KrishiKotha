"""Build and load per-district climatology (baseline) from POWER daily data."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from ...config import BASELINE_DIR
from ...models import Baseline
from .indicators import rolling_sum

WINDOW_DAYS = 15
DOY_COUNT = 366


def _circular_distance(doy: np.ndarray, target: int) -> np.ndarray:
    diff = np.abs(doy - target)
    return np.minimum(diff, DOY_COUNT - diff)


def _sorted_sample(values: np.ndarray, digits: int) -> list[float]:
    clean = values[~np.isnan(values)]
    return [round(float(v), digits) for v in np.sort(clean)]


def compute_baseline(frame: pd.DataFrame, window: int = WINDOW_DAYS) -> dict[int, dict[str, Any]]:
    """Per day-of-year climatology from a daily POWER frame.

    For each doy 1..366, samples come from all days within +/- `window` days of that doy
    (circular). Returns `{doy: {rain3_sorted, rain7_sorted, rain30_mean, tmax_mean, soil_sorted}}`.
    """
    full = frame.reindex(pd.date_range(frame.index.min(), frame.index.max(), freq="D"))
    rain = full["PRECTOTCORR"]
    rain3 = rolling_sum(rain, 3).to_numpy()
    rain7 = rolling_sum(rain, 7).to_numpy()
    rain30 = rolling_sum(rain, 30).to_numpy()
    tmax = full["T2M_MAX"].to_numpy()
    soil = full["GWETROOT"].to_numpy()
    doy = full.index.dayofyear.to_numpy()

    result: dict[int, dict[str, Any]] = {}
    for target in range(1, DOY_COUNT + 1):
        mask = _circular_distance(doy, target) <= window
        r30 = rain30[mask]
        tm = tmax[mask]
        result[target] = {
            "rain3_sorted": _sorted_sample(rain3[mask], 1),
            "rain7_sorted": _sorted_sample(rain7[mask], 1),
            "rain30_mean": round(float(np.nanmean(r30)), 2),
            "tmax_mean": round(float(np.nanmean(tm)), 2),
            "soil_sorted": _sorted_sample(soil[mask], 3),
        }
    return result


def baseline_path(district_id: str, base_dir: Path = BASELINE_DIR) -> Path:
    """Location of `data/baseline/{district}.json`."""
    return base_dir / f"{district_id}.json"


def write_baseline_file(
    district_id: str, rows: dict[int, dict[str, Any]], start_year: int, end_year: int,
    base_dir: Path = BASELINE_DIR,
) -> Path:
    """Write the baseline JSON file (compact encoding) and return its path."""
    path = baseline_path(district_id, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "district_id": district_id,
        "start_year": start_year,
        "end_year": end_year,
        "window_days": WINDOW_DAYS,
        "doy": {str(k): v for k, v in rows.items()},
    }
    path.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
    return path


def load_baseline(district_id: str, base_dir: Path = BASELINE_DIR) -> dict[int, dict[str, Any]]:
    """Load a baseline file as `{doy: row}`."""
    doc = json.loads(baseline_path(district_id, base_dir).read_text(encoding="utf-8"))
    return {int(k): v for k, v in doc["doy"].items()}


def store_baseline_rows(session: Session, district_id: str, rows: dict[int, dict[str, Any]]) -> None:
    """Upsert baseline rows into the `baselines` table (an existing `ndvi_mean` is kept unless given)."""
    for doy, row in rows.items():
        obj = session.get(Baseline, (district_id, doy)) or Baseline(district_id=district_id, doy=doy)
        obj.rain3_sorted = row["rain3_sorted"]
        obj.rain7_sorted = row["rain7_sorted"]
        obj.rain30_mean = row["rain30_mean"]
        obj.tmax_mean = row["tmax_mean"]
        obj.soil_sorted = row["soil_sorted"]
        if row.get("ndvi_mean") is not None:
            obj.ndvi_mean = row["ndvi_mean"]
        session.add(obj)
    session.commit()


def merge_ndvi_mean(
    district_id: str, rows: dict[int, dict[str, Any]], base_dir: Path = BASELINE_DIR
) -> dict[int, dict[str, Any]]:
    """Carry an already-built `ndvi_mean` over into freshly computed POWER baseline rows.

    Rebuilding the POWER baseline must not silently discard the MODIS NDVI climatology.
    """
    path = baseline_path(district_id, base_dir)
    if not path.exists():
        return rows
    old = load_baseline(district_id, base_dir)
    for doy, row in rows.items():
        if old.get(doy, {}).get("ndvi_mean") is not None:
            row["ndvi_mean"] = old[doy]["ndvi_mean"]
    return rows


def write_ndvi_mean(
    district_id: str, daily_mean: dict[int, float | None], base_dir: Path = BASELINE_DIR
) -> Path:
    """Add `ndvi_mean` to every day-of-year row of an existing baseline file (other keys untouched)."""
    path = baseline_path(district_id, base_dir)
    doc = json.loads(path.read_text(encoding="utf-8"))
    for key, row in doc["doy"].items():
        row["ndvi_mean"] = daily_mean.get(int(key))
    path.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
    return path
