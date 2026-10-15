"""CLI: fetch NASA indicators, score every district and date, write risk rows and observations.

Examples:
    python -m pipeline.run_pipeline --start 2022-05-15 --end 2022-06-30 --run final
    python -m pipeline.run_pipeline --run late              # last 30 days up to the newest IMERG day
    python -m pipeline.run_pipeline --mode snapshot         # load data/snapshots/*.json, no network

Exit code 0 means IMERG and POWER succeeded for all districts and dates (Section 7.7).
"""
from __future__ import annotations

import argparse
import sys
import time
import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.db import SessionLocal, create_all
from backend.app.models import District, Observation, PipelineRun, RiskSnapshot
from backend.app.seed import seed
from backend.app.services.nasa import imerg, modis, smap

from backend.app.services.nasa.power import build_params, fetch_power
from backend.app.services.risk.baseline import baseline_path, load_baseline
from backend.app.services.risk.scoring import score_drought, score_flood, score_salt
from backend.app.services.snapshots import load_snapshots

FETCH_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 3.0
MAX_CONSECUTIVE_FAILURES = 5
RAIN_WINDOW_DAYS = 30  # R30 needs 30 daily values ending at the effective date
TMAX_WINDOW_DAYS = 7
MAX_SOIL_AGE_DAYS = 7  # POWER soil values older than this count as missing (degraded fallback)
POWER_VERSION = "V2"  # POWER API major version; the response header reports 2.x
IMERG_VERSION = "V07"
RUN_SOURCE = {"late": "IMERG_LATE", "final": "IMERG_FINAL"}
RUN_LABEL = {"late": "GPM IMERG Late Run V07", "final": "GPM IMERG Final Run V07"}
SOIL_LABEL_SMAP = "SMAP L4 Global 9 km Root Zone Soil Moisture (sm_rootzone_pctl)"
SOIL_LABEL_POWER = "NASA POWER GWETROOT"

# earthaccess 0.17 warns about `DataGranule.size()` on every search; harmless (docs/data_sources.md).
warnings.filterwarnings("ignore", category=FutureWarning, module=r"earthaccess(\..*)?$")

RainFetcher = Callable[[date, list[dict[str, Any]], str], Mapping[str, float | None]]
PowerFetcher = Callable[[float, float, date, date], pd.DataFrame]
SoilFetcher = Callable[[date, list[dict[str, Any]]], Mapping[str, float | None]]
# (districts, end) -> (ndvi per district, product label, composite date text per district)
NdviFetcher = Callable[..., tuple[Mapping[str, float | None], str, Mapping[str, str | None]]]


@dataclass
class PowerIndicators:
    """POWER inputs for one district and effective date."""

    soil: float | None
    soil_date: date | None
    soil_stale_days: int | None
    tmax7: float | None
    tmax_date: date | None
    today_soil: float | None  # value on the effective date itself (for the observation row)
    today_tmax: float | None


@dataclass
class RunStats:
    """Mutable bookkeeping for the `PipelineRun.detail` JSON."""

    imerg_days_requested: int = 0
    imerg_failed_days: dict[str, str] = field(default_factory=dict)
    imerg_last_date: date | None = None
    power_failed: dict[str, str] = field(default_factory=dict)
    power_last_date: date | None = None
    soil_stale_max: int = 0
    skipped: list[str] = field(default_factory=list)
    written: int = 0
    smap_failed_days: dict[str, str] = field(default_factory=dict)
    smap_last_date: date | None = None
    smap_used_count: int = 0
    ndvi_product: str | None = None


def power_indicators(frame: pd.DataFrame, day: date) -> PowerIndicators:
    """Soil wetness (latest value on or before `day`) and 7-day mean `T2M_MAX` from POWER.

    A soil value more than `MAX_SOIL_AGE_DAYS` old is treated as missing: `soil` and `soil_date`
    are None, while `soil_stale_days` keeps the age of the expired value for the record.
    """
    ts = pd.Timestamp(day)
    upto = frame.loc[frame.index <= ts]

    soil_series = upto["GWETROOT"].dropna()
    soil = soil_date = stale = None
    if not soil_series.empty:
        latest_date = soil_series.index[-1].date()
        stale = (day - latest_date).days
        if stale <= MAX_SOIL_AGE_DAYS:
            soil = float(soil_series.iloc[-1])
            soil_date = latest_date

    window = frame["T2M_MAX"].loc[ts - pd.Timedelta(days=TMAX_WINDOW_DAYS - 1) : ts].dropna()
    tmax7 = float(window.mean()) if not window.empty else None
    tmax_date = window.index[-1].date() if not window.empty else None

    def on_day(column: str) -> float | None:
        if ts in frame.index and pd.notna(frame.at[ts, column]):
            return float(frame.at[ts, column])
        return None

    return PowerIndicators(
        soil=soil,
        soil_date=soil_date,
        soil_stale_days=stale,
        tmax7=tmax7,
        tmax_date=tmax_date,
        today_soil=on_day("GWETROOT"),
        today_tmax=on_day("T2M_MAX"),
    )


def rain_sums(daily: Mapping[date, float | None], day: date) -> dict[int, float | None]:
    """Rainfall totals (mm) over 3, 7 and 30 days ending at `day`; None if any day is missing."""
    sums: dict[int, float | None] = {}
    for window in (3, 7, RAIN_WINDOW_DAYS):
        values = [daily.get(day - timedelta(days=i)) for i in range(window)]
        sums[window] = None if any(v is None for v in values) else float(sum(values))  # type: ignore[arg-type]
    return sums


def _fetch_soil(
    days: list[date],
    districts: list[dict[str, Any]],
    fetch: SoilFetcher,
    stats: RunStats,
) -> dict[date, Mapping[str, float | None]]:
    """SMAP L4 root-zone soil moisture percentile per day (Section 7.6, F2.1).

    Unlike IMERG, a SMAP failure is never fatal to the pipeline: Section 7.7's exit-code
    contract only requires IMERG and POWER, and `score_district_day` already falls back to
    POWER `GWETROOT` per district when the SMAP value for that day is `None`.
    """
    soil: dict[date, Mapping[str, float | None]] = {}
    for day in days:
        try:
            values = fetch(day, districts)
        except Exception as exc:  # noqa: BLE001 - recorded, falls back to POWER per district
            stats.smap_failed_days[day.isoformat()] = f"{type(exc).__name__}: {exc}"
            print(f"SMAP {day}: FAILED, falling back to POWER ({exc})", file=sys.stderr)
            values = {d["id"]: None for d in districts}
        if any(v is not None for v in values.values()):
            stats.smap_last_date = max(stats.smap_last_date or day, day)
            stats.smap_used_count += sum(1 for v in values.values() if v is not None)
        soil[day] = values
    return soil


def _annotate(
    block: dict[str, Any],
    rain_label: str,
    day: date,
    power: PowerIndicators,
    soil_label: str,
    soil_date: date | None,
    ndvi_label: str | None = None,
    ndvi_date: date | None = None,
) -> dict[str, Any]:
    """Attach `source` and `data_date` to every input of a scoring result."""
    where: dict[str, tuple[str, date | None]] = {
        "rain3_pctl": (rain_label, day),
        "rain7_pctl": (rain_label, day),
        "rain_deficit": (rain_label, day),
        "soil_pctl": (soil_label, soil_date),
        "heat_anomaly": ("NASA POWER T2M_MAX", power.tmax_date),
        "coastal_proximity": ("Static configuration (non-NASA)", None),
        "seasonal_intrusion": ("Calendar assumption (non-NASA)", day),
        "vegetation_anomaly": (ndvi_label or "", ndvi_date),
    }
    out = dict(block)
    items = []
    for item in block["inputs"]:
        source, data_date = where.get(item["name"], ("", None))
        items.append({**item, "source": source, "data_date": data_date.isoformat() if data_date else None})
    out["inputs"] = items
    return out


def score_district_day(
    district: Mapping[str, Any],
    day: date,
    sums: Mapping[int, float | None],
    power: PowerIndicators,
    base: Mapping[str, Any],
    run: str,
    *,
    smap_soil: float | None = None,
    ndvi_anom: float | None = None,
    ndvi_product: str | None = None,
    ndvi_date: date | None = None,
) -> dict[str, Any]:
    """Score one district on one date; returns the column values for a `RiskSnapshot`.

    `sums` must hold non-null 3, 7 and 30 day rainfall. Soil input preference is SMAP L4
    (`smap_soil`, a root-zone percentile already) when available, otherwise POWER `GWETROOT`
    percentile-ranked against the baseline (Section 7.6, F2.1); this falls back silently
    (not degraded) when only one of the two is missing. A missing soil value from both
    sources, or a missing 7-day `T2M_MAX` mean, sets `degraded`; the scoring engine drops the
    missing term and renormalizes the remaining weights (Section 7.6). A missing NDVI anomaly
    uses the documented Level 1 salinity formula without `degraded` (Section 7.6, F2.2).
    """
    r3, r7, r30 = sums[3], sums[7], sums[RAIN_WINDOW_DAYS]
    assert r3 is not None and r7 is not None and r30 is not None
    flood = score_flood(
        r3=r3, b3=base["rain3_sorted"], r7=r7, b7=base["rain7_sorted"],
        soil_pctl=smap_soil, soil_wetness=power.soil, soil_baseline=base["soil_sorted"],
    )
    drought = score_drought(
        r30=r30, b30_mean=base["rain30_mean"], tmax7=power.tmax7, tbase=base["tmax_mean"],
        soil_pctl=smap_soil, soil_wetness=power.soil, soil_baseline=base["soil_sorted"],
    )
    salt = score_salt(
        float(district["coastal_distance_km"]), date_val=day, r30=r30, b30_mean=base["rain30_mean"],
        ndvi_anom=ndvi_anom,
    )
    tmax_missing = power.tmax7 is None
    soil_from_smap = smap_soil is not None
    soil_missing = bool(flood["soil_missing"])
    soil_label = SOIL_LABEL_SMAP if soil_from_smap else SOIL_LABEL_POWER
    soil_date = day if soil_from_smap else power.soil_date
    ndvi_label = f"AppEEARS {ndvi_product}" if ndvi_anom is not None and ndvi_product else None
    ndvi_date = (ndvi_date or day) if ndvi_anom is not None else None

    label = RUN_LABEL[run]
    inputs = {
        "flood": _annotate(flood, label, day, power, soil_label, soil_date, ndvi_label, ndvi_date),
        "drought": _annotate(drought, label, day, power, soil_label, soil_date, ndvi_label, ndvi_date),
        "salt": _annotate(salt, label, day, power, soil_label, soil_date, ndvi_label, ndvi_date),
        "rain_mm": {"r3": round(r3, 2), "r7": round(r7, 2), "r30": round(r30, 2)},
        "soil_wetness": power.soil,
        "soil_stale_days": power.soil_stale_days,
        "soil_source": "SMAP_L4" if soil_from_smap else "POWER_GWETROOT",
        "tmax7": None if power.tmax7 is None else round(power.tmax7, 2),
        "tmax_baseline": base["tmax_mean"],
        "rain30_baseline": base["rain30_mean"],
        "tmax_missing": tmax_missing,
        "soil_missing": soil_missing,
        "ndvi_anom": ndvi_anom,
        "ndvi_product": ndvi_product if ndvi_anom is not None else None,
    }
    sources = {
        "rain": {
            "name": label,
            "short_name": imerg.SHORT_NAMES[run],
            "version": IMERG_VERSION,
            "data_date": day.isoformat(),
        },
        "soil": {
            "name": soil_label,
            "version": smap.VERSION if soil_from_smap else POWER_VERSION,
            "data_date": soil_date.isoformat() if soil_date else None,
            "stale_days": None if soil_from_smap else power.soil_stale_days,
        },
        "tmax": {
            "name": "NASA POWER T2M_MAX",
            "version": POWER_VERSION,
            "data_date": power.tmax_date.isoformat() if power.tmax_date else None,
        },
    }
    if ndvi_anom is not None and ndvi_product:
        sources["ndvi"] = {
            "name": f"AppEEARS {ndvi_product} NDVI anomaly",
            "version": ndvi_product.split(".")[-1],
            "data_date": ndvi_date.isoformat() if ndvi_date else None,  # start of the 16-day composite
        }
    return {
        "drought_score": drought["score"],
        "flood_score": flood["score"],
        "salt_score": salt["score"],
        "drought_level": drought["level"],
        "flood_level": flood["level"],
        "salt_level": salt["level"],
        "inputs": inputs,
        "sources": sources,
        "degraded": bool(flood["degraded"] or drought["degraded"] or salt["degraded"]),
    }


def _fetch_rain(
    days: list[date],
    districts: list[dict[str, Any]],
    run: str,
    fetch: RainFetcher,
    stats: RunStats,
    sleep: Callable[[float], None],
) -> dict[date, Mapping[str, float | None]]:
    """District-box rainfall for each day; failures are recorded, not raised.

    Each day is tried up to `FETCH_ATTEMPTS` times (Earthdata login and downloads drop
    connections now and then). After `MAX_CONSECUTIVE_FAILURES` days in a row fail, the
    remaining days are marked failed without further attempts.
    """
    daily: dict[date, Mapping[str, float | None]] = {}
    stats.imerg_days_requested = len(days)
    consecutive = 0
    for i, day in enumerate(days):
        if consecutive >= MAX_CONSECUTIVE_FAILURES:
            for rest in days[i:]:
                stats.imerg_failed_days[rest.isoformat()] = "skipped after repeated failures"
            print(f"IMERG: {consecutive} failures in a row, giving up", file=sys.stderr)
            break
        error: Exception | None = None
        for attempt in range(FETCH_ATTEMPTS):
            try:
                daily[day] = fetch(day, districts, run)
                error = None
                break
            except Exception as exc:  # noqa: BLE001 - recorded below, never silently dropped
                error = exc
                if attempt < FETCH_ATTEMPTS - 1:
                    sleep(RETRY_BACKOFF_SECONDS * (2**attempt))
        if error is not None:
            consecutive += 1
            stats.imerg_failed_days[day.isoformat()] = f"{type(error).__name__}: {error}"
            print(f"IMERG {day}: FAILED ({error})", file=sys.stderr)
            continue
        consecutive = 0
        if any(v is not None for v in daily[day].values()):
            stats.imerg_last_date = max(stats.imerg_last_date or day, day)
        print(f"IMERG {run} {day}: ok")
    return daily


def run_pipeline(
    session: Session,
    start: date,
    end: date,
    run: str = "late",
    *,
    rain_fetcher: RainFetcher = imerg.district_means,  # type: ignore[assignment]
    power_fetcher: PowerFetcher = fetch_power,
    soil_fetcher: SoilFetcher = smap.district_values,  # type: ignore[assignment]
    ndvi_fetcher: NdviFetcher | None = modis.fetch_current_ndvi,
    sleep: Callable[[float], None] = time.sleep,
) -> PipelineRun:
    """Score every district for each date in `[start, end]` and record a `PipelineRun` row."""
    if run not in RUN_SOURCE:
        raise ValueError(f"run must be 'late' or 'final', got {run!r}")
    if end < start:
        raise ValueError("--end must not be before --start")
    started = datetime.now(timezone.utc)
    stats = RunStats()

    seed(session)
    district_rows = list(session.scalars(select(District).order_by(District.id)))
    districts = [
        {"id": d.id, "lat": d.lat, "lon": d.lon, "coastal_distance_km": d.coastal_distance_km}
        for d in district_rows
    ]
    days = [start - timedelta(days=RAIN_WINDOW_DAYS - 1) + timedelta(days=i)
            for i in range((end - start).days + RAIN_WINDOW_DAYS)]
    scored_days = [d for d in days if d >= start]

    rain = _fetch_rain(days, districts, run, rain_fetcher, stats, sleep)
    rain_by_district = {
        d["id"]: {day: values.get(d["id"]) for day, values in rain.items()} for d in districts
    }

    # SMAP L4 soil moisture (Section 7.6, F2.1): one lookup per scored day, every district at
    # once. Never fatal: a failure here just leaves `soil_by_district[did][day]` as None, and
    # `score_district_day` falls back to POWER `GWETROOT` for that district and day.
    soil = _fetch_soil(scored_days, districts, soil_fetcher, stats)
    soil_by_district = {
        d["id"]: {day: values.get(d["id"]) for day, values in soil.items()} for d in districts
    }

    # MODIS NDVI anomaly (Section 7.6, F2.2): one AppEEARS point task per run, reused across
    # every scored day (a 16-day composite does not change daily). `ndvi_fetcher` already
    # swallows its own errors and returns `None` per district when AppEEARS is pending or
    # unreachable; the salinity formula then uses the documented Level 1 fallback.
    if ndvi_fetcher is not None:
        ndvi_by_district, ndvi_product, ndvi_dates = ndvi_fetcher(districts, end)
    else:
        ndvi_by_district, ndvi_product = {d["id"]: None for d in districts}, None
        ndvi_dates = {d["id"]: None for d in districts}
    stats.ndvi_product = ndvi_product
    ndvi_available = any(v is not None for v in ndvi_by_district.values())
    ndvi_anom_count = 0

    existing_snaps = {
        (s.district_id, s.date): s
        for s in session.scalars(select(RiskSnapshot).where(RiskSnapshot.date >= start, RiskSnapshot.date <= end))
    }
    existing_obs = {
        (o.district_id, o.date, o.source, o.variable): o
        for o in session.scalars(select(Observation).where(Observation.date >= start, Observation.date <= end))
    }

    def put_obs(district_id: str, day: date, source: str, variable: str, value: float | None, version: str) -> None:
        key = (district_id, day, source, variable)
        obj = existing_obs.get(key) or Observation(
            district_id=district_id, date=day, source=source, variable=variable
        )
        obj.value, obj.product_version = value, version
        session.add(obj)
        existing_obs[key] = obj

    power_end = min(end, date.today())
    power_start = start - timedelta(days=TMAX_WINDOW_DAYS)
    for district in districts:
        did = district["id"]
        try:
            frame = power_fetcher(district["lat"], district["lon"], power_start, power_end)
            base = load_baseline(did)
        except Exception as exc:  # noqa: BLE001 - one district must not block the rest
            stats.power_failed[did] = f"{type(exc).__name__}: {exc}"
            print(f"{did}: POWER/baseline FAILED ({exc})", file=sys.stderr)
            continue

        written_before = stats.written
        ndvi_raw = ndvi_by_district.get(did)
        ndvi_when = date.fromisoformat(ndvi_dates[did][:10]) if ndvi_dates.get(did) else None
        for day in scored_days:
            power = power_indicators(frame, day)
            if power.soil_date:
                stats.power_last_date = max(stats.power_last_date or power.soil_date, power.soil_date)
                stats.soil_stale_max = max(stats.soil_stale_max, power.soil_stale_days or 0)
            daily_rain = rain_by_district[did]
            smap_soil = soil_by_district[did].get(day)
            put_obs(did, day, RUN_SOURCE[run], "precip_mm", daily_rain.get(day), IMERG_VERSION)
            put_obs(did, day, "POWER", "tmax_c", power.today_tmax, POWER_VERSION)
            put_obs(did, day, "POWER", "soil_wetness", power.today_soil, POWER_VERSION)
            put_obs(did, day, "SMAP_L4", "rz_pctl", smap_soil, smap.VERSION)
            if ndvi_raw is not None:
                put_obs(did, day, "MODIS_MOD13Q1", "ndvi", ndvi_raw, (ndvi_product or "").split(".")[-1])

            sums = rain_sums(daily_rain, day)
            if any(v is None for v in sums.values()):
                stats.skipped.append(f"{did} {day}: incomplete IMERG window")
                continue
            base_row = base[day.timetuple().tm_yday]
            # Anomaly = current NDVI minus the 2003-2020 mean for the same 16-day period, i.e. the
            # baseline row at the day-of-year of the composite the value came from (not of `day`).
            # Without a baseline (`python -m pipeline.build_ndvi_baseline` not completed) this is
            # None, which selects the documented Level 1 salinity formula.
            ndvi_base = (
                base.get(ndvi_when.timetuple().tm_yday, {}).get("ndvi_mean") if ndvi_when else None
            )
            ndvi_anom = (
                round(ndvi_raw - float(ndvi_base), 4)
                if ndvi_raw is not None and ndvi_base is not None else None
            )
            ndvi_anom_count += ndvi_anom is not None
            values = score_district_day(
                district, day, sums, power, base_row, run,
                smap_soil=smap_soil, ndvi_anom=ndvi_anom, ndvi_product=ndvi_product,
                ndvi_date=ndvi_when,
            )
            snap = existing_snaps.get((did, day)) or RiskSnapshot(district_id=did, date=day)
            for key, value in values.items():
                setattr(snap, key, value)
            snap.created_at = datetime.now(timezone.utc)
            session.add(snap)
            existing_snaps[(did, day)] = snap
            stats.written += 1
        print(f"{did}: {stats.written - written_before} of {len(scored_days)} dates scored")

    imerg_ok = not stats.imerg_failed_days
    power_ok = not stats.power_failed
    if stats.written == 0:
        status = "failed"
    elif imerg_ok and power_ok and not stats.skipped:
        status = "ok"
    else:
        status = "partial"

    detail = {
        "mode": "live",
        "run": run,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "lookback_days": RAIN_WINDOW_DAYS - 1,
        "sources": {
            "IMERG": {
                "status": "ok" if imerg_ok else "partial" if len(stats.imerg_failed_days) < stats.imerg_days_requested else "failed",
                "product": f"{imerg.SHORT_NAMES[run]} {IMERG_VERSION}",
                "days_requested": stats.imerg_days_requested,
                "failed_days": stats.imerg_failed_days,
                "last_data_date": stats.imerg_last_date.isoformat() if stats.imerg_last_date else None,
            },
            "POWER": {
                "status": "ok" if power_ok else "partial" if len(stats.power_failed) < len(districts) else "failed",
                "parameters": "GWETROOT, T2M_MAX",
                "failed_districts": stats.power_failed,
                "last_data_date": stats.power_last_date.isoformat() if stats.power_last_date else None,
                "max_soil_stale_days": stats.soil_stale_max,
                "request_example": build_params(
                    districts[0]["lat"], districts[0]["lon"], power_start, power_end, ("GWETROOT", "T2M_MAX")
                ),
            },
            "SMAP": {
                "status": "ok" if stats.smap_last_date and not stats.smap_failed_days else (
                    "partial" if stats.smap_last_date else "unavailable_fallback_to_power"
                ),
                "product": f"{smap.SHORT_NAME} v{smap.VERSION}",
                "failed_days": stats.smap_failed_days,
                "last_data_date": stats.smap_last_date.isoformat() if stats.smap_last_date else None,
                "used_values": stats.smap_used_count,
                "note": "Soil input falls back to POWER GWETROOT per district/day when a SMAP value is unavailable (Section 7.6, F2.1); this never affects the pipeline's overall ok/partial/failed status.",
            },
            "MODIS": {
                "status": (
                    "ok" if ndvi_anom_count
                    else "ndvi_without_baseline_fallback" if ndvi_available
                    else "unavailable_fallback_no_ndvi"
                ),
                "product": stats.ndvi_product or modis.PRODUCT,
                "anomaly_values_used": ndvi_anom_count,
                "composite_dates": {k: v for k, v in ndvi_dates.items() if v},
                "reason": None if ndvi_anom_count else (
                    "NDVI was retrieved but the 2003-2020 baseline mean is not populated, so no anomaly "
                    "can be computed" if ndvi_available else
                    "AppEEARS point task was still pending (or unreachable) within this pipeline "
                    "run's poll window"
                ) + "; the documented Level 1 salinity formula without NDVI is used instead, with "
                "degraded=false (Section 7.6, F2.2). See docs/data_sources.md.",
            },
        },
        "districts": len(districts),
        "dates": len(scored_days),
        "snapshots_written": stats.written,
        "skipped": stats.skipped[:50],
        "skipped_count": len(stats.skipped),
    }
    record = PipelineRun(
        started_at=started, finished_at=datetime.now(timezone.utc), status=status, detail=detail
    )
    session.add(record)
    session.commit()
    return record


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Krishi Kotha data pipeline")
    parser.add_argument("--mode", choices=("live", "snapshot"), default="live")
    parser.add_argument("--start", type=date.fromisoformat, help="first date to score (YYYY-MM-DD)")
    parser.add_argument("--end", type=date.fromisoformat, help="last date to score (YYYY-MM-DD)")
    parser.add_argument(
        "--run", choices=sorted(RUN_SOURCE), default="late",
        help="IMERG product: 'final' for event replay, 'late' (default) for recent dates",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the process exit code."""
    args = _parse_args(argv)
    create_all()
    if args.mode == "snapshot":
        with SessionLocal() as session:
            seed(session)
            counts = load_snapshots(session)
        print(f"Loaded snapshots (no network used): {counts}")
        return 0

    if get_settings().data_mode == "snapshot":
        print("DATA_MODE=snapshot forbids live runs; use --mode snapshot.", file=sys.stderr)
        return 2
    end, start = args.end, args.start
    if end is None:
        from backend.app.services.nasa.cmr import latest_granule_date

        latest = latest_granule_date(imerg.SHORT_NAMES[args.run], imerg.VERSION)
        if latest is None:
            print(f"CMR lists no {imerg.SHORT_NAMES[args.run]} granules", file=sys.stderr)
            return 1
        end = latest.date()
    if start is None:
        start = end - timedelta(days=RAIN_WINDOW_DAYS - 1)
    with SessionLocal() as session:
        seed(session)
        ids = [d.id for d in session.scalars(select(District))]
    if any(not baseline_path(i).exists() for i in ids):
        print("Baselines missing; run `python -m pipeline.build_baseline` first.", file=sys.stderr)
        return 1

    with SessionLocal() as session:
        record = run_pipeline(session, start, end, args.run)
        d = record.detail
    print(
        f"Pipeline {record.status}: {d['snapshots_written']} snapshots, "
        f"IMERG {d['sources']['IMERG']['status']} (last {d['sources']['IMERG']['last_data_date']}), "
        f"POWER {d['sources']['POWER']['status']} (last {d['sources']['POWER']['last_data_date']})"
    )
    return 0 if record.status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
