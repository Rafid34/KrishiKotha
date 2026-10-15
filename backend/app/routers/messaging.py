"""Messaging routers: simulator SMS and future gateway webhooks (Sections 7.2, 9)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import SimReply, SimSmsOut, SimSmsRequest
from ..services.messaging.handler import handle_inbound_sms

router = APIRouter(prefix="/api", tags=["messaging"])


@router.post("/sim/sms", response_model=SimSmsOut)
def sim_sms(payload: SimSmsRequest, db: Session = Depends(get_db)) -> SimSmsOut:
    """Simulate receiving an inbound SMS message from a farmer."""
    result = handle_inbound_sms(
        from_number=payload.from_,
        body=payload.body,
        db=db,
        as_of_date=payload.date,
        channel="sim",
    )
    return SimSmsOut(
        replies=[SimReply(text=r["text"]) for r in result["replies"]],
        subscriber_id=result.get("subscriber_id"),
    )
