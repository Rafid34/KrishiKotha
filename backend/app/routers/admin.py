"""Admin routes: broadcast preview and send (F2.7, Sections 7.2, 9).

Every route here requires a valid `X-Admin-Key` header.
"""
from __future__ import annotations

import hmac
import logging

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..errors import ApiError, not_found
from ..models import District, MessageLog, Subscriber
from ..schemas import BroadcastOut, BroadcastRequest
from ..services.messaging.gateway_loader import outbound_gateway
from ..services.messaging.handler import current_advice

log = logging.getLogger("krishi_kotha")

LEVEL_RANK = {"low": 0, "moderate": 1, "high": 2}


def require_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    """Reject the request with 401 unless `X-Admin-Key` matches `ADMIN_API_KEY`."""
    expected = get_settings().admin_api_key
    if not expected or not x_admin_key or not hmac.compare_digest(
        x_admin_key.encode("utf-8"), expected.encode("utf-8")
    ):
        raise ApiError(401, "unauthorized", "Missing or invalid X-Admin-Key")


router = APIRouter(
    prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin_key)]
)


@router.post("/broadcast", response_model=BroadcastOut)
def broadcast(payload: BroadcastRequest, db: Session = Depends(get_db)) -> BroadcastOut:
    """Preview (default) or send current advice to active subscribers in a district.

    A subscriber is a recipient when the advice rule chosen for their crop and growth
    stage is at or above `min_level`. With `dry_run=true` nothing is sent or logged.
    """
    if db.get(District, payload.district_id) is None:
        raise not_found(f"District '{payload.district_id}' does not exist")

    subscribers = (
        db.query(Subscriber)
        .filter_by(district_id=payload.district_id, active=True)
        .order_by(Subscriber.id)
        .all()
    )
    minimum = LEVEL_RANK[payload.min_level]
    targets = []
    for subscriber in subscribers:
        advice = current_advice(db, subscriber.district_id, subscriber.crop_id, payload.date)
        if advice.rule_id != "none_low" and LEVEL_RANK[advice.level] >= minimum:
            targets.append((subscriber, advice))

    sample = targets[0][1].text_bn if targets else None
    if payload.dry_run or not targets:
        return BroadcastOut(recipients=len(targets), sample_text_bn=sample, sent=0)

    gateway, channel = outbound_gateway()
    sent = 0
    for subscriber, advice in targets:
        if gateway.send_sms(subscriber.phone_e164, advice.text_bn):
            sent += 1
            db.add(
                MessageLog(
                    subscriber_id=subscriber.id,
                    direction="out",
                    channel=channel,
                    body=advice.text_bn,
                    rule_id=advice.rule_id,
                )
            )
    db.commit()
    log.info("Broadcast to %s: %d of %d sent via %s", payload.district_id, sent, len(targets), channel)
    return BroadcastOut(recipients=len(targets), sample_text_bn=sample, sent=sent)
