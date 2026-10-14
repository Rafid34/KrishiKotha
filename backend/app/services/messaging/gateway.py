"""Gateway interface for SMS and voice delivery (Sections 6, 7.2)."""
from __future__ import annotations

from abc import ABC, abstractmethod


class MessagingGateway(ABC):
    """Abstract interface for sending SMS and interacting with voice channels."""

    @abstractmethod
    def send_sms(self, to: str, text: str) -> bool:
        """Send an SMS message to a phone number."""
        ...
