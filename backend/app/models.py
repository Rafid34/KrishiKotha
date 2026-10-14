"""ORM models (Section 7.1)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    """Timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


class District(Base):
    __tablename__ = "districts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name_en: Mapped[str] = mapped_column(String)
    name_bn: Mapped[str] = mapped_column(String)
    division: Mapped[str] = mapped_column(String)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    coastal_distance_km: Mapped[float] = mapped_column(Float)
    upstream_bbox: Mapped[Any | None] = mapped_column(JSON, nullable=True)


class Crop(Base):
    __tablename__ = "crops"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name_en: Mapped[str] = mapped_column(String)
    name_bn: Mapped[str] = mapped_column(String)
    stages: Mapped[Any] = mapped_column(JSON)


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (UniqueConstraint("district_id", "date", "source", "variable"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String)
    variable: Mapped[str] = mapped_column(String)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    product_version: Mapped[str] = mapped_column(String, default="")


class Baseline(Base):
    __tablename__ = "baselines"

    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), primary_key=True)
    doy: Mapped[int] = mapped_column(Integer, primary_key=True)
    rain3_sorted: Mapped[Any] = mapped_column(JSON)
    rain7_sorted: Mapped[Any] = mapped_column(JSON)
    rain30_mean: Mapped[float] = mapped_column(Float)
    tmax_mean: Mapped[float] = mapped_column(Float)
    soil_sorted: Mapped[Any] = mapped_column(JSON)
    ndvi_mean: Mapped[float | None] = mapped_column(Float, nullable=True)


class RiskSnapshot(Base):
    __tablename__ = "risk_snapshots"
    __table_args__ = (UniqueConstraint("district_id", "date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    drought_score: Mapped[float] = mapped_column(Float)
    flood_score: Mapped[float] = mapped_column(Float)
    salt_score: Mapped[float] = mapped_column(Float)
    drought_level: Mapped[str] = mapped_column(String)
    flood_level: Mapped[str] = mapped_column(String)
    salt_level: Mapped[str] = mapped_column(String)
    inputs: Mapped[Any] = mapped_column(JSON, default=dict)
    sources: Mapped[Any] = mapped_column(JSON, default=dict)
    degraded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone_e164: Mapped[str] = mapped_column(String)
    phone_hash: Mapped[str] = mapped_column(String, index=True)
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"))
    crop_id: Mapped[str] = mapped_column(ForeignKey("crops.id"))
    language: Mapped[str] = mapped_column(String, default="bn")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    messages: Mapped[list["MessageLog"]] = relationship(back_populates="subscriber")


class MessageLog(Base):
    __tablename__ = "message_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscriber_id: Mapped[int | None] = mapped_column(ForeignKey("subscribers.id"), nullable=True)
    direction: Mapped[str] = mapped_column(String)
    channel: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(String)
    rule_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    subscriber: Mapped[Subscriber | None] = relationship(back_populates="messages")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, default="ok")
    detail: Mapped[Any] = mapped_column(JSON, default=dict)
