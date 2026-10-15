"""Messaging routers: simulator SMS, audio, and Twilio webhooks (Sections 7.2, 9)."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..errors import ApiError, not_found
from ..models import MessageLog, Subscriber
from ..schemas import SimReply, SimSmsOut, SimSmsRequest
from ..services.advice.composer import compose_advice
from ..services.messaging.gateway_loader import TwilioDisabledError, load_twilio_gateway
from ..services.messaging.handler import current_advice, handle_inbound_sms, hash_phone
from ..services.messaging.tts import (
    AudioNotFoundError,
    TtsUnavailableError,
    audio_url,
    ensure_audio,
    prepare_audio,
)

if TYPE_CHECKING:  # never executed: Twilio is imported only when enabled
    from ..services.messaging.twilio_gateway import TwilioGateway

log = logging.getLogger("krishi_kotha")

router = APIRouter(prefix="/api", tags=["messaging"])

VOICE_FALLBACK_SAY = "Voice advice is not available right now. Please check your text messages."


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


@router.get("/audio/{filename}")
def get_audio(filename: str) -> FileResponse:
    """Serve cached Bangla MP3, generating it on first request (F2.4).

    404 when the file name is unknown; 503 with a JSON message when gTTS fails.
    """
    try:
        path = ensure_audio(filename)
    except AudioNotFoundError:
        raise not_found("Audio file not found") from None
    except TtsUnavailableError as exc:
        raise ApiError(503, "unavailable", str(exc)) from exc
    return FileResponse(path, media_type="audio/mpeg")


def _twilio_gateway() -> TwilioGateway:
    """Load the Twilio adapter or answer 404 while the flag is off."""
    try:
        return load_twilio_gateway()
    except TwilioDisabledError as exc:
        raise not_found(str(exc)) from exc
    except RuntimeError as exc:  # TwilioConfigError: enabled but misconfigured
        raise ApiError(503, "unavailable", str(exc)) from exc


async def _verified_form(request: Request, gateway: TwilioGateway) -> dict[str, str]:
    """Parse Twilio's form body and reject the request unless its signature is valid."""
    form = await request.form()
    params = {key: str(value) for key, value in form.items()}
    url = get_settings().public_base_url.rstrip("/") + request.url.path
    if request.url.query:
        url += "?" + request.url.query
    signature = request.headers.get("X-Twilio-Signature")
    if not gateway.validate_signature(url, params, signature):
        raise ApiError(403, "forbidden", "Invalid Twilio signature")
    if not params.get("From"):
        raise ApiError(400, "bad_request", "Missing From field")
    return params


@router.post("/sms/inbound")
async def sms_inbound(request: Request, db: Session = Depends(get_db)) -> Response:
    """Twilio messaging webhook: reply with TwiML containing the advice messages."""
    gateway = _twilio_gateway()
    params = await _verified_form(request, gateway)
    result = await run_in_threadpool(
        handle_inbound_sms, params["From"], params.get("Body", ""), db, None, "sms"
    )
    xml = gateway.sms_twiml([r["text"] for r in result["replies"]])
    return Response(content=xml, media_type="text/xml")


def _voice_audio_url(db: Session, from_number: str) -> str | None:
    """Audio URL for the caller's current advice (help message when not registered)."""
    subscriber = (
        db.query(Subscriber).filter_by(phone_hash=hash_phone(from_number), active=True).first()
    )
    if subscriber is None:
        text, rule_id = compose_advice("help").text_bn, "help"
    else:
        advice = current_advice(db, subscriber.district_id, subscriber.crop_id)
        text, rule_id = advice.text_bn, advice.rule_id
    try:
        filename = prepare_audio(text)
    except (TtsUnavailableError, AudioNotFoundError) as exc:
        log.warning("Voice webhook without audio: %s", exc)
        return None
    db.add(
        MessageLog(
            subscriber_id=subscriber.id if subscriber else None,
            direction="out",
            channel="voice",
            body=text,
            rule_id=rule_id,
        )
    )
    db.commit()
    base = get_settings().public_base_url.rstrip("/")
    return base + audio_url(filename)


@router.post("/voice/inbound")
async def voice_inbound(request: Request, db: Session = Depends(get_db)) -> Response:
    """Twilio voice webhook: TwiML that plays the cached Bangla MP3 through the public URL.

    The optional `Digits` field is accepted but unused: callers always hear their current advice.
    """
    gateway = _twilio_gateway()
    params = await _verified_form(request, gateway)
    url = await run_in_threadpool(_voice_audio_url, db, params["From"])
    xml = gateway.voice_twiml(url, VOICE_FALLBACK_SAY)
    return Response(content=xml, media_type="text/xml")
