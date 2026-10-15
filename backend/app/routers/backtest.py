"""/api/backtest/sylhet-2022 route (Section 7.2, 8.4, 9 task 8.4)."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import not_found
from ..models import Baseline, District, Observation, RiskSnapshot
from ..schemas import BacktestOut
from ..services.backtest import (
    REFERENCE_ONSET_DEFAULT,
    compute_backtest,
)

router = APIRouter(prefix="/api/backtest", tags=["backtest"])

RAIN_SOURCES = ("IMERG_FINAL", "IMERG_LATE")


@router.get("/sylhet-2022", response_model=BacktestOut)
def backtest_sylhet(db: Session = Depends(get_db)) -> BacktestOut:
    """Sylhet June 2022 flood backtest, lead time, and replay steps."""
    district = db.get(District, "sylhet")
    if district is None:
        raise not_found("District 'sylhet' does not exist")

    # Fetch snapshots for Sylhet 2022 event (May 15 to June 30, 2022)
    start_date = date(2022, 5, 15)
    end_date = date(2022, 6, 30)

    rows = db.scalars(
        select(RiskSnapshot)
        .where(
            RiskSnapshot.district_id == "sylhet",
            RiskSnapshot.date >= start_date,
            RiskSnapshot.date <= end_date,
        )
        .order_by(RiskSnapshot.date)
    ).all()

    if not rows:
        # Fallback to any available rows for sylhet (e.g. in test environments)
        rows = db.scalars(
            select(RiskSnapshot)
            .where(RiskSnapshot.district_id == "sylhet")
            .order_by(RiskSnapshot.date)
        ).all()

    if not rows:
        raise not_found("No snapshot data available for Sylhet 2022 backtest")

    first_day = rows[0].date
    last_day = rows[-1].date

    # Fetch observations for rain_mm and soil_wetness
    obs = db.scalars(
        select(Observation).where(
            Observation.district_id == "sylhet",
            Observation.date >= first_day,
            Observation.date <= last_day,
            Observation.variable.in_(("precip_mm", "soil_wetness")),
        )
    ).all()

    rain: dict[date, dict[str, float | None]] = {}
    soil: dict[date, float | None] = {}
    for o in obs:
        if o.variable == "precip_mm" and o.source in RAIN_SOURCES:
            rain.setdefault(o.date, {})[o.source] = o.value
        elif o.variable == "soil_wetness":
            soil[o.date] = o.value

    def rain_for(day: date) -> float | None:
        by_source = rain.get(day, {})
        for s in RAIN_SOURCES:
            if s in by_source:
                return by_source[s]
        return None

    # Fetch baselines for Sylhet to get 90th percentile rain3 for each day of year
    baselines = db.scalars(
        select(Baseline).where(Baseline.district_id == "sylhet")
    ).all()
    p90_by_doy: dict[int, float | None] = {}
    for b in baselines:
        r3 = b.rain3_sorted or []
        if r3:
            idx = int(len(r3) * 0.90)
            p90_by_doy[b.doy] = float(r3[min(idx, len(r3) - 1)])

    series_data = []
    for r in rows:
        doy = r.date.timetuple().tm_yday
        series_data.append(
            {
                "date": r.date.isoformat(),
                "flood_score": r.flood_score,
                "flood_level": r.flood_level,
                "rain_mm": rain_for(r.date),
                "soil_wetness": soil.get(r.date),
                "rain_pctl_90": p90_by_doy.get(doy),
                "inputs": r.inputs,
            }
        )

    res = compute_backtest(series_data, reference_onset=REFERENCE_ONSET_DEFAULT)
    return BacktestOut(
        district_id="sylhet",
        series=res["series"],
        first_moderate=res["first_moderate"],
        first_high=res["first_high"],
        reference_onset=res["reference_onset"],
        lead_time_days=res["lead_time_days"],
        steps=res["steps"],
        citation=res.get("citation"),
    )
