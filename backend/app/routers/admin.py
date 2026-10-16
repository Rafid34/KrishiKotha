"""Admin routes: broadcast preview and send (F2.7, Sections 7.2, 9).

Every route here requires a valid `X-Admin-Key` header.
"""
from __future__ import annotations

import hmac
import logging
import threading
from datetime import date as dt_date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import SessionLocal, get_db
from ..errors import ApiError, not_found
from ..models import District, MessageLog, PipelineRun, Subscriber
from ..schemas import (
    BroadcastOut,
    BroadcastRequest,
    PipelineRunRequest,
    PipelineRunStartOut,
)
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


def default_pipeline_runner(
    record_id: int, start: dt_date, end: dt_date, run: str, mode: str
) -> None:
    from pipeline.run_pipeline import run_pipeline

    with SessionLocal() as session:
        try:
            run_pipeline(session, start, end, run, record_id=record_id)
        except Exception as exc:
            log.exception("Pipeline run %d failed: %s", record_id, exc)
            rec = session.get(PipelineRun, record_id)
            if rec is not None:
                rec.finished_at = datetime.now(timezone.utc)
                rec.status = "failed"
                rec.detail = {"error": str(exc)}
                session.commit()


pipeline_runner = default_pipeline_runner


@router.post("/pipeline/run", response_model=PipelineRunStartOut)
def trigger_pipeline_run(
    payload: PipelineRunRequest,
    db: Session = Depends(get_db),
) -> PipelineRunStartOut:
    """Start a pipeline run in the background."""
    if get_settings().data_mode == "snapshot" and payload.mode == "live":
        raise ApiError(409, "conflict", "DATA_MODE=snapshot forbids live runs")

    active = db.scalars(select(PipelineRun).where(PipelineRun.status == "running")).first()
    if active is not None:
        raise ApiError(409, "conflict", f"Pipeline run {active.id} is already active")

    if payload.as_of is not None:
        end = payload.as_of
    else:
        from ..services.nasa import cmr, imerg
        latest = cmr.latest_granule_date(imerg.SHORT_NAMES.get(payload.run, "GPM_3IMERGDL"), imerg.VERSION)
        end = latest.date() if latest is not None else dt_date.today()

    start = end - timedelta(days=29)

    record = PipelineRun(
        started_at=datetime.now(timezone.utc),
        status="running",
        detail={"mode": payload.mode, "run": payload.run, "start": start.isoformat(), "end": end.isoformat()},
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    thread = threading.Thread(
        target=pipeline_runner,
        args=(record.id, start, end, payload.run, payload.mode),
        daemon=True,
    )
    thread.start()

    return PipelineRunStartOut(run_id=record.id, status="started")

