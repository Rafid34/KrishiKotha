"""Meta routes: /api/health, /api/sources, /api/pipeline/status."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import VERSION, get_settings
from ..db import get_db
from ..errors import not_found
from ..models import Observation, PipelineRun
from ..schemas import HealthOut, PipelineStatusOut, SourceOut
from ..timeutil import iso_utc

router = APIRouter(prefix="/api", tags=["meta"])

# `observation_source` is the value of `observations.source` used to find the last data date.
DATASETS: tuple[dict[str, str], ...] = (
    {
        "name": "NASA POWER Daily (AG community)",
        "short_name": "POWER_DAILY",
        "version": "V2",
        "resolution": "0.5 x 0.625 degree (MERRA-2 grid), daily",
        "latency": "about 2 days (observed 2026-10)",
        "url": "https://power.larc.nasa.gov/docs/services/api/temporal/daily/",
        "observation_source": "POWER",
    },
    {
        "name": "GPM IMERG Late Run, daily",
        "short_name": "GPM_3IMERGDL",
        "version": "V07",
        "resolution": "0.1 degree, daily",
        "latency": "about 14 hours",
        "url": "https://doi.org/10.5067/GPM/IMERGDL/DAY/07",
        "observation_source": "IMERG_LATE",
    },
    {
        "name": "GPM IMERG Final Run, daily",
        "short_name": "GPM_3IMERGDF",
        "version": "V07",
        "resolution": "0.1 degree, daily",
        "latency": "months (CMR newest granule was about a year old in 2026-10)",
        "url": "https://doi.org/10.5067/GPM/IMERGDF/DAY/07",
        "observation_source": "IMERG_FINAL",
    },
)


@router.get("/health", response_model=HealthOut)
def health() -> dict[str, str]:
    """Liveness check including the configured data mode."""
    return {"status": "ok", "data_mode": get_settings().data_mode, "version": VERSION}


@router.get("/sources", response_model=list[SourceOut])
def sources(db: Session = Depends(get_db)) -> list[dict[str, str | None]]:
    """Datasets in use, with the newest observation date stored for each (no network access)."""
    last_dates = dict(
        db.execute(
            select(Observation.source, func.max(Observation.date))
            .where(Observation.value.is_not(None))
            .group_by(Observation.source)
        ).all()
    )
    out: list[dict[str, str | None]] = []
    for ds in DATASETS:
        last = last_dates.get(ds["observation_source"])
        entry: dict[str, str | None] = {k: v for k, v in ds.items() if k != "observation_source"}
        entry["last_data_date"] = last.isoformat() if last else None
        out.append(entry)
    return out


@router.get("/pipeline/status", response_model=PipelineStatusOut)
def pipeline_status(db: Session = Depends(get_db)) -> dict[str, object]:
    """The most recently started `PipelineRun` row."""
    run = db.scalars(
        select(PipelineRun).order_by(PipelineRun.started_at.desc(), PipelineRun.id.desc()).limit(1)
    ).first()
    if run is None:
        raise not_found("No pipeline run has been recorded")
    return {
        "id": run.id,
        "started_at": iso_utc(run.started_at),
        "finished_at": iso_utc(run.finished_at),
        "status": run.status,
        "detail": run.detail or {},
    }
