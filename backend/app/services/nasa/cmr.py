"""NASA CMR granule discovery (no login required)."""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ...config import get_settings
from .offline import ensure_online


class CmrError(RuntimeError):
    """Raised when CMR is unreachable or returns an unusable payload."""


def latest_granule_date(
    short_name: str, version: str, *, client: httpx.Client | None = None
) -> datetime | None:
    """Return the start time (UTC) of the newest granule of a collection, or None if none exist."""
    ensure_online("NASA CMR")
    url = f"{get_settings().cmr_base.rstrip('/')}/granules.json"
    params = {
        "short_name": short_name,
        "version": version,
        "sort_key": "-start_date",
        "page_size": "1",
    }
    owns_client = client is None
    client = client or httpx.Client(timeout=60.0)
    try:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        entries = resp.json()["feed"]["entry"]
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise CmrError(f"CMR query for {short_name} v{version} failed: {exc}") from exc
    finally:
        if owns_client:
            client.close()
    if not entries:
        return None
    start = entries[0].get("time_start")
    if not start:
        raise CmrError(f"CMR granule for {short_name} v{version} has no time_start")
    return datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(timezone.utc)
