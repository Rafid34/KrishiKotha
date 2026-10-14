"""UTC timestamp helpers (SQLite returns naive datetimes; all stored values are UTC)."""
from __future__ import annotations

from datetime import datetime, timezone


def as_utc(value: datetime) -> datetime:
    """Treat a naive datetime as UTC and convert aware ones to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def iso_utc(value: datetime | None) -> str | None:
    """ISO 8601 string ending in `Z` (seconds precision), or None."""
    if value is None:
        return None
    return as_utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str) -> datetime:
    """Parse an ISO 8601 string (with `Z` or offset) into an aware UTC datetime."""
    return as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
