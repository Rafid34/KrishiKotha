"""NASA POWER daily point client with file cache and retry."""
from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from ...config import CACHE_DIR, get_settings

PARAMETERS = ("PRECTOTCORR", "T2M_MAX", "RH2M", "GWETROOT")
FILL_VALUE = -999.0
POWER_CACHE_DIR = CACHE_DIR / "power"


class PowerError(RuntimeError):
    """Raised when POWER cannot be reached or returns an unusable payload."""


def build_params(
    lat: float, lon: float, start: date, end: date, parameters: tuple[str, ...] = PARAMETERS
) -> dict[str, str]:
    """Query parameters for the POWER daily point endpoint."""
    return {
        "parameters": ",".join(parameters),
        "community": "AG",
        "longitude": f"{lon:.4f}",
        "latitude": f"{lat:.4f}",
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }


def cache_path(
    lat: float, lon: float, start: date, end: date, parameters: tuple[str, ...], cache_dir: Path
) -> Path:
    """Cache file keyed by (lat, lon, start, end, parameters)."""
    key = f"{lat:.4f}|{lon:.4f}|{start}|{end}|{','.join(parameters)}"
    return cache_dir / f"{hashlib.sha1(key.encode()).hexdigest()}.json"


def parse_power_json(payload: dict[str, Any]) -> pd.DataFrame:
    """Parse `properties.parameter` into a DataFrame indexed by date; -999 becomes NaN."""
    try:
        params = payload["properties"]["parameter"]
    except (KeyError, TypeError) as exc:
        raise PowerError("POWER response has no properties.parameter") from exc
    frame = pd.DataFrame(params)
    frame.index = pd.to_datetime(frame.index, format="%Y%m%d")
    frame.index.name = "date"
    frame = frame.astype(float).sort_index()
    return frame.mask(frame == FILL_VALUE)


def _get_json(
    url: str, params: dict[str, str], client: httpx.Client, retries: int, backoff: float,
    sleep: Callable[[float], None],
) -> dict[str, Any]:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            resp = client.get(url, params=params)
            if resp.status_code in (429, 500, 502, 503, 504):
                raise PowerError(f"POWER returned HTTP {resp.status_code}")
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, PowerError, ValueError) as exc:
            last = exc
            if attempt < retries - 1:
                sleep(backoff * (2**attempt))
    raise PowerError(f"POWER request failed after {retries} attempts: {last}")


def fetch_power(
    lat: float,
    lon: float,
    start: date,
    end: date,
    parameters: tuple[str, ...] = PARAMETERS,
    *,
    client: httpx.Client | None = None,
    cache_dir: Path | None = POWER_CACHE_DIR,
    retries: int = 4,
    backoff: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> pd.DataFrame:
    """Return a daily DataFrame (index `date`, one column per parameter) for a point.

    Results are cached on disk; pass `cache_dir=None` to disable caching.
    """
    path = cache_path(lat, lon, start, end, parameters, cache_dir) if cache_dir else None
    if path is not None and path.exists():
        return parse_power_json(json.loads(path.read_text(encoding="utf-8")))

    url = f"{get_settings().power_api_base.rstrip('/')}/temporal/daily/point"
    params = build_params(lat, lon, start, end, parameters)
    owns_client = client is None
    client = client or httpx.Client(timeout=120.0)
    try:
        payload = _get_json(url, params, client, retries, backoff, sleep)
    finally:
        if owns_client:
            client.close()

    frame = parse_power_json(payload)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
    return frame
