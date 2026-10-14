"""Simulator gateway: records messages in memory, makes no outbound network requests."""
from __future__ import annotations

from dataclasses import dataclass, field

from .gateway import MessagingGateway


@dataclass
class SimMessage:
    to: str
    text: str


class SimGateway(MessagingGateway):
    """In-memory simulator gateway for testing and demo without real SMS costs or network access."""

    def __init__(self) -> None:
        self.sent_messages: list[SimMessage] = []

    def send_sms(self, to: str, text: str) -> bool:
        self.sent_messages.append(SimMessage(to=to, text=text))
        return True

    def clear(self) -> None:
        self.sent_messages.clear()


sim_gateway = SimGateway()
