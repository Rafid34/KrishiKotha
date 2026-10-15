"""Twilio adapter for SMS and voice (F2.5). Imported only when `TWILIO_ENABLED=true`.

Nothing else in the app may import this module at module level; routes load it through
`load_twilio_gateway`, which refuses to run while the flag is off.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse

from .gateway import MessagingGateway


class TwilioConfigError(RuntimeError):
    """Twilio is enabled but required settings are missing."""


class TwilioGateway(MessagingGateway):
    """Sends SMS through the Twilio REST API and builds TwiML for inbound webhooks."""

    def __init__(self, account_sid: str, auth_token: str, from_number: str) -> None:
        if not account_sid or not auth_token:
            raise TwilioConfigError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are required.")
        self._from_number = from_number
        self._auth_token = auth_token
        self._validator = RequestValidator(auth_token)
        self._client = Client(account_sid, auth_token)

    def send_sms(self, to: str, text: str) -> bool:
        """Send one SMS; returns False when Twilio rejects it."""
        if not self._from_number:
            raise TwilioConfigError("TWILIO_FROM_NUMBER is required to send SMS.")
        try:
            self._client.messages.create(to=to, from_=self._from_number, body=text)
        except Exception:  # TwilioRestException, network errors; caller counts failures
            return False
        return True

    def validate_signature(
        self, url: str, params: Mapping[str, str], signature: str | None
    ) -> bool:
        """Check the `X-Twilio-Signature` header against the public URL and form fields."""
        if not signature:
            return False
        return bool(self._validator.validate(url, dict(params), signature))

    @staticmethod
    def sms_twiml(texts: Sequence[str]) -> str:
        """TwiML with one `<Message>` per reply text."""
        response = MessagingResponse()
        for text in texts:
            response.message(text)
        return str(response)

    @staticmethod
    def voice_twiml(audio_url: str | None, fallback_say: str) -> str:
        """TwiML that plays `audio_url`, or speaks `fallback_say` when no audio exists."""
        response = VoiceResponse()
        if audio_url:
            response.play(audio_url)
        else:
            response.say(fallback_say, language="en-US")
        response.hangup()
        return str(response)
