"""Chooses the outbound gateway without importing Twilio unless it is enabled (F2.5)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ...config import get_settings
from .gateway import MessagingGateway
from .sim_gateway import sim_gateway

if TYPE_CHECKING:  # type checkers only; never executed at runtime
    from .twilio_gateway import TwilioGateway


class TwilioDisabledError(RuntimeError):
    """Raised when Twilio functionality is requested while `TWILIO_ENABLED=false`."""


def load_twilio_gateway() -> TwilioGateway:
    """Import and build the Twilio adapter. Raises `TwilioDisabledError` when the flag is off."""
    settings = get_settings()
    if not settings.twilio_enabled:
        raise TwilioDisabledError("Twilio gateway is disabled (TWILIO_ENABLED=false).")
    from .twilio_gateway import TwilioGateway  # deferred: only reached when enabled

    return TwilioGateway(
        settings.twilio_account_sid,
        settings.twilio_auth_token,
        settings.twilio_from_number,
    )


def outbound_gateway() -> tuple[MessagingGateway, str]:
    """Return the gateway for sending SMS and the MessageLog channel name (`sms` or `sim`)."""
    if get_settings().twilio_enabled:
        return load_twilio_gateway(), "sms"
    return sim_gateway, "sim"
