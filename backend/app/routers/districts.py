"""/api/districts and /api/crops."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Crop, District
from ..schemas import CropOut, DistrictOut

router = APIRouter(prefix="/api", tags=["districts"])


@router.get("/districts", response_model=list[DistrictOut])
def list_districts(db: Session = Depends(get_db)) -> list[District]:
    """All districts with coordinates and names in both languages."""
    return list(db.scalars(select(District).order_by(District.id)))


@router.get("/crops", response_model=list[CropOut])
def list_crops(db: Session = Depends(get_db)) -> list[Crop]:
    """All crops with names in both languages."""
    return list(db.scalars(select(Crop).order_by(Crop.id)))
