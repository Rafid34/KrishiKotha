"""/api/risk routes: map data, time series, explanation (read-only)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import not_found
from ..models import District, Observation, RiskSnapshot
from ..schemas import (
    CoastalFactor,
    DistrictRisk,
    ExplainOut,
    Hazard,
    HazardExplain,
    HazardScore,
    RiskMapOut,
    RiskSeriesOut,
    SeriesPoint,
)

router = APIRouter(prefix="/api/risk", tags=["risk"])

HAZARDS: tuple[str, ...] = ("drought", "flood", "salt")
RAIN_SOURCES = ("IMERG_FINAL", "IMERG_LATE")  # Final Run wins when both exist for a date
COASTAL_INPUT = "coastal_proximity"


def _require_district(db: Session, district_id: str) -> District:
    district = db.get(District, district_id)
    if district is None:
        raise not_found(f"District '{district_id}' does not exist")
    return district


def _hazard_score(row: RiskSnapshot, hazard: str) -> HazardScore:
    return HazardScore(score=getattr(row, f"{hazard}_score"), level=getattr(row, f"{hazard}_level"))


@router.get("", response_model=RiskMapOut, response_model_exclude_none=True)
def risk_map(
    date: date | None = Query(None, description="YYYY-MM-DD; default is the latest date with data"),
    hazard: Hazard | None = Query(None, description="Limit the output to one hazard"),
    db: Session = Depends(get_db),
) -> RiskMapOut:
    """Scores and levels for every district on one date."""
    day = date or db.scalar(select(func.max(RiskSnapshot.date)))
    if day is None:
        raise not_found("No risk data available")
    rows = db.scalars(
        select(RiskSnapshot).where(RiskSnapshot.date == day).order_by(RiskSnapshot.district_id)
    ).all()
    if not rows:
        raise not_found(f"No risk data for {day.isoformat()}")
    wanted = (hazard,) if hazard else HAZARDS
    districts = [
        DistrictRisk(
            district_id=row.district_id,
            degraded=bool(row.degraded),
            **{h: _hazard_score(row, h) for h in wanted},
        )
        for row in rows
    ]
    return RiskMapOut(date=day.isoformat(), districts=districts)


@router.get("/{district_id}", response_model=RiskSeriesOut)
def risk_series(
    district_id: str,
    days: int = Query(60, ge=1, le=365, description="Window length in days (max 365)"),
    date: date | None = Query(None, description="YYYY-MM-DD; window ends at this date (default: latest snapshot)"),
    db: Session = Depends(get_db),
) -> RiskSeriesOut:
    """Daily scores with rainfall and soil wetness for the `days` days ending at `date`."""
    _require_district(db, district_id)
    last = date or db.scalar(
        select(func.max(RiskSnapshot.date)).where(RiskSnapshot.district_id == district_id)
    )
    if last is None:
        return RiskSeriesOut(district_id=district_id, series=[])
    first = last - timedelta(days=days - 1)
    rows = db.scalars(
        select(RiskSnapshot)
        .where(
            RiskSnapshot.district_id == district_id,
            RiskSnapshot.date >= first,
            RiskSnapshot.date <= last,
        )
        .order_by(RiskSnapshot.date)
    ).all()

    obs = db.scalars(
        select(Observation).where(
            Observation.district_id == district_id,
            Observation.date >= first,
            Observation.date <= last,
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
        for source in RAIN_SOURCES:
            if source in by_source:
                return by_source[source]
        return None

    series = [
        SeriesPoint(
            date=r.date.isoformat(),
            drought_score=r.drought_score,
            flood_score=r.flood_score,
            salt_score=r.salt_score,
            rain_mm=rain_for(r.date),
            soil_wetness=soil.get(r.date),
        )
        for r in rows
    ]
    return RiskSeriesOut(district_id=district_id, series=series)


def _explain_block(row: RiskSnapshot, hazard: str) -> HazardExplain:
    block: dict[str, Any] = (row.inputs or {}).get(hazard, {})

    def tidy(number: Any) -> Any:
        return round(number, 4) if isinstance(number, float) else number

    items = []
    coastal: CoastalFactor | None = None
    for item in block.get("inputs", []):
        if item.get("name") == COASTAL_INPUT:
            # Multiplier on the additive sum, not a weighted term: report it separately so the
            # displayed weights sum to 1.0. The stored scores and formula are unchanged.
            value = item.get("value")
            coastal = CoastalFactor(
                name=COASTAL_INPUT,
                raw=tidy(item.get("raw")),
                value=tidy(value),
                multiplier=None if value is None else round(value / 100.0, 4),
                source=item.get("source", ""),
                data_date=item.get("data_date"),
            )
            continue
        items.append(
            {
                "name": item.get("name", ""),
                "value": tidy(item.get("value")),
                "weight": item.get("weight", 0.0),
                "source": item.get("source", ""),
                "data_date": item.get("data_date"),
                "raw": tidy(item.get("raw")),
            }
        )
    return HazardExplain(
        score=getattr(row, f"{hazard}_score"),
        level=getattr(row, f"{hazard}_level"),
        inputs=items,
        coastal_factor=coastal,
    )


@router.get("/{district_id}/explain", response_model=ExplainOut)
def risk_explain(
    district_id: str,
    date: date | None = Query(None, description="YYYY-MM-DD; default is the district's latest date"),
    db: Session = Depends(get_db),
) -> ExplainOut:
    """Inputs, weights, sources and data dates behind each score."""
    _require_district(db, district_id)
    query = select(RiskSnapshot).where(RiskSnapshot.district_id == district_id)
    if date is not None:
        query = query.where(RiskSnapshot.date == date)
    else:
        query = query.order_by(RiskSnapshot.date.desc())
    row = db.scalars(query.limit(1)).first()
    if row is None:
        when = date.isoformat() if date else "any date"
        raise not_found(f"No risk snapshot for '{district_id}' on {when}")
    return ExplainOut(
        district_id=district_id,
        date=row.date.isoformat(),
        flood=_explain_block(row, "flood"),
        drought=_explain_block(row, "drought"),
        salt=_explain_block(row, "salt"),
        degraded=bool(row.degraded),
    )
