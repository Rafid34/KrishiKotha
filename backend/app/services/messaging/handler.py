"""Shared inbound SMS handler used by simulator and delivery gateways (Sections 7.1, 7.4, 9)."""
from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from ...models import MessageLog, RiskSnapshot, Subscriber
from ..advice.composer import compose_advice
from ..advice.rules import select_advice_rule
from ..advice.stages import get_crop_stage
from .parser import parse_message

PHONE_SALT = "krishi_kotha_salt"


def hash_phone(phone_e164: str) -> str:
    """Compute SHA-256 with salt for subscriber phone lookup (Section 7.1)."""
    normalized = phone_e164.strip()
    return hashlib.sha256(f"{PHONE_SALT}:{normalized}".encode("utf-8")).hexdigest()


def handle_inbound_sms(
    from_number: str,
    body: str,
    db: Session,
    as_of_date: date | None = None,
    channel: str = "sim",
) -> dict[str, Any]:
    """Handle an inbound SMS message: parse, upsert subscriber, log replies, return message dict.

    Returns:
        dict with 'replies': list[dict[str, str]] and 'subscriber_id': int | None.
    """
    parsed = parse_message(body)
    phone_hash = hash_phone(from_number)

    subscriber = db.query(Subscriber).filter_by(phone_hash=phone_hash).first()

    if parsed.command == "register":
        assert parsed.district_id is not None
        assert parsed.crop_id is not None

        if subscriber is not None:
            subscriber.phone_e164 = from_number
            subscriber.district_id = parsed.district_id
            subscriber.crop_id = parsed.crop_id
            subscriber.active = True
        else:
            subscriber = Subscriber(
                phone_e164=from_number,
                phone_hash=phone_hash,
                district_id=parsed.district_id,
                crop_id=parsed.crop_id,
                language="bn",
                active=True,
            )
            db.add(subscriber)

        db.flush()

        # 1. Welcome message reply
        welcome_advice = compose_advice("welcome")
        welcome_text = welcome_advice.text_bn
        db.add(
            MessageLog(
                subscriber_id=subscriber.id,
                direction="out",
                channel=channel,
                body=welcome_text,
                rule_id="welcome",
            )
        )

        # 2. Advice message reply based on latest snapshot
        if as_of_date:
            snapshot = (
                db.query(RiskSnapshot)
                .filter_by(district_id=parsed.district_id, date=as_of_date)
                .first()
            )
        else:
            snapshot = (
                db.query(RiskSnapshot)
                .filter_by(district_id=parsed.district_id)
                .order_by(RiskSnapshot.date.desc())
                .first()
            )

        if snapshot is not None:
            stage_info = get_crop_stage(parsed.crop_id, snapshot.date)
            rule_result = select_advice_rule(
                flood_score=snapshot.flood_score,
                drought_score=snapshot.drought_score,
                salt_score=snapshot.salt_score,
                crop_id=parsed.crop_id,
                stage_key=stage_info.stage_key,
                sensitivities=stage_info.sensitivities,
            )
            advice_obj = compose_advice(rule_result.rule_id)
            advice_text = advice_obj.text_bn
            rule_id = rule_result.rule_id
        else:
            advice_obj = compose_advice("none_low")
            advice_text = advice_obj.text_bn
            rule_id = "none_low"

        db.add(
            MessageLog(
                subscriber_id=subscriber.id,
                direction="out",
                channel=channel,
                body=advice_text,
                rule_id=rule_id,
            )
        )

        db.commit()
        db.refresh(subscriber)

        return {
            "replies": [{"text": welcome_text}, {"text": advice_text}],
            "subscriber_id": subscriber.id,
        }

    elif parsed.command == "stop":
        sub_id = None
        if subscriber is not None:
            subscriber.active = False
            sub_id = subscriber.id

        stopped_text = compose_advice("stopped").text_bn
        db.add(
            MessageLog(
                subscriber_id=sub_id,
                direction="out",
                channel=channel,
                body=stopped_text,
                rule_id="stopped",
            )
        )
        db.commit()

        return {
            "replies": [{"text": stopped_text}],
            "subscriber_id": sub_id,
        }

    else:  # "help" or "unknown" or unrecognized command
        sub_id = subscriber.id if subscriber else None
        help_text = compose_advice("help").text_bn
        db.add(
            MessageLog(
                subscriber_id=sub_id,
                direction="out",
                channel=channel,
                body=help_text,
                rule_id="help",
            )
        )
        db.commit()

        return {
            "replies": [{"text": help_text}],
            "subscriber_id": sub_id,
        }
