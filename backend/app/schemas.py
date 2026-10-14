"""Pydantic response models for the read API (Section 7.2)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

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


class ExplainOut(BaseModel):
    district_id: str
    date: str
    flood: HazardExplain
    drought: HazardExplain
    salt: HazardExplain
    degraded: bool


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
