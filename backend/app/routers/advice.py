"""POST /api/advice endpoint (Sections 7.2, 7.4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import not_found
from ..models import Crop, District, RiskSnapshot
from ..schemas import AdviceOut, AdviceRequest
from ..services.advice.composer import compose_advice
from ..services.advice.rules import select_advice_rule
from ..services.advice.stages import get_crop_stage

router = APIRouter(prefix="/api", tags=["advice"])


@router.post("/advice", response_model=AdviceOut)
def get_advice(payload: AdviceRequest, db: Session = Depends(get_db)) -> AdviceOut:
    """Generate Bangla and English crop advice based on hazard scores and crop growth stage."""
    # 1. District validation
    district = db.get(District, payload.district_id)
    if not district:
        raise not_found(f"District '{payload.district_id}' does not exist")

    # 2. Crop validation
    crop = db.get(Crop, payload.crop_id)
    if not crop:
        raise not_found(f"Crop '{payload.crop_id}' does not exist")

    # 3. Snapshot retrieval
    if payload.date:
        snapshot = (
            db.query(RiskSnapshot)
            .filter_by(district_id=payload.district_id, date=payload.date)
            .first()
        )
        if not snapshot:
            raise not_found(
                f"No risk snapshot for district '{payload.district_id}' on date '{payload.date}'"
            )
    else:
        snapshot = (
            db.query(RiskSnapshot)
            .filter_by(district_id=payload.district_id)
            .order_by(RiskSnapshot.date.desc())
            .first()
        )
        if not snapshot:
            raise not_found(f"No risk snapshots found for district '{payload.district_id}'")

    # 4. Crop growth stage for the snapshot date
    stage_info = get_crop_stage(payload.crop_id, snapshot.date)

    # 5. Rule evaluation
    rule_result = select_advice_rule(
        flood_score=snapshot.flood_score,
        drought_score=snapshot.drought_score,
        salt_score=snapshot.salt_score,
        crop_id=payload.crop_id,
        stage_key=stage_info.stage_key,
        sensitivities=stage_info.sensitivities,
    )

    # 6. Compose advice
    composed = compose_advice(rule_result.rule_id)

    return AdviceOut(
        rule_id=rule_result.rule_id,
        text_bn=composed.text_bn,
        text_en=composed.text_en,
        hazard=rule_result.hazard,
        level=rule_result.level,
        audio_url=None,
    )
