"""Pydantic response models for the read API (Section 7.2)."""
from __future__ import annotations

from datetime import date as dt_date
from typing import Any, Literal

from pydantic import BaseModel, Field

Level = Literal["low", "moderate", "high"]
Hazard = Literal["drought", "flood", "salt"]


class HealthOut(BaseModel):
    status: str
    data_mode: str
    version: str


class DistrictOut(BaseModel):
    id: str
    name_en: str
    name_bn: str
    lat: float
    lon: float
    division: str


class CropOut(BaseModel):
    id: str
    name_en: str
    name_bn: str


class HazardScore(BaseModel):
    score: float
    level: Level


class DistrictRisk(BaseModel):
    """One map row. Hazards not requested through `hazard=` are omitted."""

    district_id: str
    drought: HazardScore | None = None
    flood: HazardScore | None = None
    salt: HazardScore | None = None
    degraded: bool


class RiskMapOut(BaseModel):
    date: str
    districts: list[DistrictRisk]


class SeriesPoint(BaseModel):
    date: str
    drought_score: float
    flood_score: float
    salt_score: float
    rain_mm: float | None
    soil_wetness: float | None


class RiskSeriesOut(BaseModel):
    district_id: str
    series: list[SeriesPoint]


class ExplainInput(BaseModel):
    name: str
    value: float | None
    weight: float
    source: str
    data_date: str | None
    raw: float | int | None = None


class CoastalFactor(BaseModel):
    """Salinity multiplier (`s_coast / 100`); applies to the whole additive sum, so it has no weight."""

    name: str
    raw: float | None  # coastal distance in km
    value: float | None  # s_coast sub-score, 0 to 100
    multiplier: float | None  # value / 100
    source: str
    data_date: str | None


class HazardExplain(BaseModel):
    score: float
    level: Level
    inputs: list[ExplainInput]
    coastal_factor: CoastalFactor | None = None  # salt only


class SoilSourceInfo(BaseModel):
    """Which soil input fed the score; `fallback` is true when POWER replaced SMAP (F2.1)."""

    source: str | None  # `SMAP_L4`, `POWER_GWETROOT`, or null for rows stored before Phase 10
    name: str | None = None
    version: str | None = None
    data_date: str | None = None
    fallback: bool = False


class NdviInfo(BaseModel):
    """NDVI anomaly status; `used` false means the Level 1 salinity formula was applied (F2.2)."""

    used: bool
    anomaly: float | None = None
    product: str | None = None
    version: str | None = None
    data_date: str | None = None
    fallback_reason: str | None = None


class ExplainOut(BaseModel):
    district_id: str
    date: str
    flood: HazardExplain
    drought: HazardExplain
    salt: HazardExplain
    degraded: bool
    soil_source: SoilSourceInfo | None = None
    ndvi: NdviInfo | None = None


class SourceOut(BaseModel):
    name: str
    short_name: str
    version: str
    resolution: str
    latency: str
    last_data_date: str | None
    url: str


class PipelineStatusOut(BaseModel):
    id: int
    started_at: str | None
    finished_at: str | None
    status: str
    detail: dict[str, Any]


class AdviceRequest(BaseModel):
    district_id: str
    crop_id: str
    date: dt_date | None = None
    language: str = "bn"


class AdviceOut(BaseModel):
    rule_id: str
    text_bn: str
    text_en: str
    hazard: str | None = None
    level: str
    audio_url: str | None = None


class SimSmsRequest(BaseModel):
    from_: str = Field(..., alias="from")
    body: str
    date: dt_date | None = None

    model_config = {"populate_by_name": True}


class SimReply(BaseModel):
    text: str


class SimSmsOut(BaseModel):
    replies: list[SimReply]
    subscriber_id: int | None = None


class ReplayStep(BaseModel):
    step: int
    label: str
    label_bn: str | None = None
    date: str | None = None


class BacktestPoint(BaseModel):
    date: str
    flood_score: float
    flood_level: str
    rain_mm: float | None = None
    soil_wetness: float | None = None
    rain_pctl_90: float | None = None


class BacktestOut(BaseModel):
    district_id: str
    series: list[BacktestPoint]
    first_moderate: str | None = None
    first_high: str | None = None
    reference_onset: str
    lead_time_days: int | None = None
    steps: list[ReplayStep]
    citation: str | None = None

