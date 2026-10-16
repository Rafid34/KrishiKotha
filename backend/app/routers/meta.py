"""Meta routes: /api/health, /api/sources, /api/pipeline/status."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import VERSION, get_settings
from ..db import get_db
from ..errors import not_found
from ..models import Observation, PipelineRun
from ..schemas import HealthOut, LayerOut, PipelineStatusOut, SourceOut
from ..services.risk.scoring import SCORING_CONSTANTS

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
    {
        "name": "SMAP L4 Global 3-hourly 9 km Surface and Root Zone Soil Moisture (root zone percentile)",
        "short_name": "SPL4SMGP",
        "version": "008",
        "resolution": "9 km EASE-Grid 2.0, 3-hourly (one granule per day near 06:00 UTC used)",
        "latency": "about 2 to 3 days (newest CMR granule 2026-10-11 on 2026-10-15)",
        "url": "https://doi.org/10.5067/T5RUATAQREF8",
        "observation_source": "SMAP_L4",
    },
    {
        "name": "MODIS Terra Vegetation Indices 16-day 250 m (NDVI) via AppEEARS",
        "short_name": "MOD13Q1",
        "version": "061",
        "resolution": "250 m, 16-day composite (point extraction at district centroids)",
        "latency": "asynchronous AppEEARS task; often still pending after a minute, so NDVI may fall back",
        "url": "https://appeears.earthdatacloud.nasa.gov/",
        "observation_source": "MODIS_MOD13Q1",
    },
    {
        "name": "NASA GIBS imagery layers (IMERG precipitation rate, MODIS NDVI), map overlay only",
        "short_name": "GIBS",
        "version": "WMTS, no product version",
        "resolution": "GoogleMapsCompatible tile matrix sets, levels 6 and 9, daily or 16-day imagery",
        "latency": "imagery for a date can be missing; the map then says so",
        "url": "https://nasa-gibs.github.io/gibs-api-docs/",
        "observation_source": "GIBS",
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


@router.get("/scoring")
def scoring() -> dict[str, object]:
    """Scoring weights and thresholds (Section 7.6), read from the code that computes the scores.

    Kept apart from `/api/sources` so that route stays a plain list of datasets (Section 7.2);
    the Method page reads both, so the formulas it shows always match the engine.
    """
    return {"constants": SCORING_CONSTANTS}


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


GIBS_LAYERS: tuple[dict[str, str], ...] = (
    {
        "id": "IMERG_Precipitation_Rate",
        "title": "NASA IMERG precipitation rate",
        "tile_matrix_set": "GoogleMapsCompatible_Level6",
        "format": "png",
        "coverage_start": "2000-06-01",
    },
    {
        "id": "MODIS_Terra_L3_NDVI_16Day",
        "title": "MODIS Terra NDVI (16-day)",
        "tile_matrix_set": "GoogleMapsCompatible_Level9",
        "format": "png",
        "coverage_start": "2000-03-05",
    },
    {
        "id": "MODIS_Terra_NDVI_8Day",
        "title": "MODIS Terra NDVI (rolling 8-day)",
        "tile_matrix_set": "GoogleMapsCompatible_Level9",
        "format": "png",
        "coverage_start": "2025-02-12",
    },
)


@router.get("/layers", response_model=list[LayerOut])
def layers() -> list[dict[str, str]]:
    """GIBS layer definitions for map overlays (Section 7.2)."""
    return [dict(layer) for layer in GIBS_LAYERS]

