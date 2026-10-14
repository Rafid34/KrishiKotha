"""Guard that stops every outbound NASA call when `DATA_MODE=snapshot`."""
from __future__ import annotations

from ...config import get_settings


class OfflineModeError(RuntimeError):
    """Raised when code tries to reach the network while `DATA_MODE=snapshot`."""


def ensure_online(what: str) -> None:
    """Raise `OfflineModeError` in snapshot mode; call this right before any network access."""
    if get_settings().data_mode == "snapshot":
        raise OfflineModeError(f"{what} needs network access but DATA_MODE=snapshot")
