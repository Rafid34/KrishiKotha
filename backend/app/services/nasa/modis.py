"""Level 2: AppEEARS point task client for NDVI (Section 2.2, task 10.3).

Confirmed live against the real AppEEARS REST API on 2026-10-15 (`docs/data_sources.md`):
`POST {base}/login` with Earthdata Basic Auth returns a bearer token; `GET {base}/product/
MOD13Q1.061` lists the layer `_250m_16_days_NDVI` exactly as the spec assumes; a submitted
point task for the 8 district centroids stayed `pending` for more than a minute (NASA's
processing queue, not an error). AppEEARS point tasks are therefore asynchronous on a
timescale this application cannot block on, so `fetch_current_ndvi` polls for a bounded time
and returns `None` for every district if the task has not finished, which the scoring engine
already documents as a Level 1 fallback with `degraded: false` (Section 7.6, F2.2) rather than
a failure.
"""
from __future__ import annotations

import csv
import io
import json
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping

import httpx

from ...config import CACHE_DIR, STATIC_DIR, get_settings
from .offline import ensure_online

MODIS_CACHE_DIR = CACHE_DIR / "modis"
PENDING_TASKS_FILE = MODIS_CACHE_DIR / "pending_tasks.json"
APPEEARS_BASE = "https://appeears.earthdatacloud.nasa.gov/api/"

PRODUCT = "MOD13Q1.061"
LAYER = "_250m_16_days_NDVI"
# Confirmed via GET {base}/product/VNP13A1.002 on 2026-10-15: used only if MOD13Q1 is
# unavailable for the requested period (Section 2.2).
FALLBACK_PRODUCT = "VNP13A1.002"
FALLBACK_LAYER = "500_m_16_days_NDVI"
# AppEEARS applies the product scale factor itself: the real result CSV (task 14f992a9..., checked
# 2026-10-15) holds NDVI such as 0.4311, not the raw integer 4311. Values outside the product's valid
# range (-0.2 to 1.0; the fill value is -0.3) are discarded.
NDVI_VALID_MIN = -0.2
NDVI_VALID_MAX = 1.0
DEFAULT_WINDOW_DAYS = 45  # enough to span at least two 16-day composites


class ModisError(RuntimeError):
    """Raised when AppEEARS cannot be reached, authenticated, or returns an unusable payload."""


def load_districts() -> list[dict[str, Any]]:
    """Districts from `data/static/districts.json`."""
    return json.loads((STATIC_DIR / "districts.json").read_text(encoding="utf-8"))


def login(client: httpx.Client) -> str:
    """`POST {base}/login` with Earthdata credentials (Basic Auth); returns the bearer token."""
    ensure_online("AppEEARS login")
    settings = get_settings()
    if not settings.earthdata_username or not settings.earthdata_password:
        raise ModisError("EARTHDATA_USERNAME/EARTHDATA_PASSWORD not set")
    resp = client.post(
        f"{APPEEARS_BASE}login", auth=(settings.earthdata_username, settings.earthdata_password)
    )
    if resp.status_code != 200:
        raise ModisError(f"AppEEARS login failed: HTTP {resp.status_code}")
    token = resp.json().get("token")
    if not token:
        raise ModisError("AppEEARS login response has no token")
    return token


def submit_task(
    districts: Iterable[Mapping[str, Any]],
    start: date,
    end: date,
    token: str,
    *,
    client: httpx.Client,
    task_name: str = "krishi_kotha_ndvi",
    product: str = PRODUCT,
    layer: str = LAYER,
) -> str:
    """Submit an AppEEARS `point` task for the district centroids; returns the task id."""
    payload = {
        "task_type": "point",
        "task_name": task_name,
        "params": {
            "dates": [{"startDate": start.strftime("%m-%d-%Y"), "endDate": end.strftime("%m-%d-%Y")}],
            "layers": [{"product": product, "layer": layer}],
            "coordinates": [
                {"latitude": float(d["lat"]), "longitude": float(d["lon"]), "id": d["id"]}
                for d in districts
            ],
        },
    }
    resp = client.post(f"{APPEEARS_BASE}task", headers={"Authorization": f"Bearer {token}"}, json=payload)
    if resp.status_code not in (200, 201, 202):
        raise ModisError(f"AppEEARS task submission failed: HTTP {resp.status_code}: {resp.text[:200]}")
    task_id = resp.json().get("task_id")
    if not task_id:
        raise ModisError("AppEEARS task response has no task_id")
    return task_id


def task_status(task_id: str, token: str, *, client: httpx.Client) -> str:
    """`GET {base}/status/{task_id}`; returns the status string (`pending`, `done`, ...).

    Observed live (2026-10-15): while a task is queued the endpoint answers HTTP 200, but once it
    has finished it answers HTTP 303 (redirect to `/task/{id}`) with `"status": "done"` in the body.
    The redirect is deliberately not followed; the body already says everything needed.
    """
    resp = client.get(f"{APPEEARS_BASE}status/{task_id}", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code not in (200, 303):
        raise ModisError(f"AppEEARS status check failed: HTTP {resp.status_code}")
    try:
        body = resp.json()
    except ValueError as exc:
        raise ModisError("AppEEARS status response is not JSON") from exc
    if body.get("status"):
        return str(body["status"])
    # While a task is being processed the body has a `progress` block and no `status` key.
    return "processing" if "progress" in body else "unknown"


def download_point_csv(task_id: str, token: str, *, client: httpx.Client) -> list[dict[str, str]]:
    """Download the task's point-results CSV and return it as a list of row dicts."""
    resp = client.get(f"{APPEEARS_BASE}bundle/{task_id}", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code != 200:
        raise ModisError(f"AppEEARS bundle listing failed: HTTP {resp.status_code}")
    files = resp.json().get("files", [])
    csv_file = next((f for f in files if f["file_name"].endswith("-results.csv")), None)
    if csv_file is None:
        raise ModisError("AppEEARS bundle has no *-results.csv file")
    # File downloads redirect to cloud storage; httpx drops the Authorization header on the
    # cross-origin hop, so following the redirect does not leak the token.
    file_resp = client.get(
        f"{APPEEARS_BASE}bundle/{task_id}/{csv_file['file_id']}",
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=True,
    )
    if file_resp.status_code != 200:
        raise ModisError(f"AppEEARS file download failed: HTTP {file_resp.status_code}")
    return list(csv.DictReader(io.StringIO(file_resp.content.decode("utf-8"))))


def _ndvi_column(rows: list[dict[str, str]], product: str, layer: str) -> str:
    prefix = f"{product.replace('.', '_')}_{layer}"
    for key in rows[0].keys() if rows else ():
        if key.startswith(prefix):
            return key
    raise ModisError(f"no NDVI column starting with {prefix!r} in AppEEARS results")


def _valid_ndvi_rows(rows: list[dict[str, str]], product: str, layer: str):
    """Yield `(district_id, composite_date_text, ndvi)` for rows with a valid NDVI value."""
    if not rows:
        return
    column = _ndvi_column(rows, product, layer)
    for row in rows:
        did, raw, day = row.get("ID"), row.get(column, ""), row.get("Date", "")
        if not did or not raw or not day:
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        if NDVI_VALID_MIN <= value <= NDVI_VALID_MAX:
            yield did, day, value


def latest_ndvi_readings(
    rows: list[dict[str, str]], product: str = PRODUCT, layer: str = LAYER
) -> dict[str, tuple[str, float]]:
    """Most recent valid `(composite_date, ndvi)` per district `ID` (fill values are skipped)."""
    latest: dict[str, tuple[str, float]] = {}
    for did, day, value in _valid_ndvi_rows(rows, product, layer):
        if did not in latest or day > latest[did][0]:
            latest[did] = (day, value)
    return latest


def latest_ndvi_by_district(
    rows: list[dict[str, str]], product: str = PRODUCT, layer: str = LAYER
) -> dict[str, float | None]:
    """Most recent valid NDVI value per district `ID` column (fill values are skipped)."""
    return {did: value for did, (_, value) in latest_ndvi_readings(rows, product, layer).items()}


BASELINE_START_YEAR = 2003
BASELINE_END_YEAR = 2020
COMPOSITE_DAYS = 16


def composite_doy(doy: int) -> int:
    """Start day-of-year of the 16-day MOD13Q1 composite that contains `doy` (1, 17, ..., 353).

    MOD13Q1 composites restart every 1 January, so the same start DOY is comparable across years.
    """
    return min(353, 1 + COMPOSITE_DAYS * ((doy - 1) // COMPOSITE_DAYS))


def build_ndvi_baseline(
    rows: list[dict[str, str]],
    product: str = PRODUCT,
    layer: str = LAYER,
    start_year: int = BASELINE_START_YEAR,
    end_year: int = BASELINE_END_YEAR,
) -> dict[str, dict[int, float]]:
    """Mean NDVI per district and composite start day-of-year over `start_year`..`end_year`."""
    sums: dict[tuple[str, int], list[float]] = {}
    for did, day, value in _valid_ndvi_rows(rows, product, layer):
        when = date.fromisoformat(day[:10])
        if start_year <= when.year <= end_year:
            sums.setdefault((did, when.timetuple().tm_yday), []).append(value)
    out: dict[str, dict[int, float]] = {}
    for (did, doy), values in sums.items():
        out.setdefault(did, {})[doy] = round(sum(values) / len(values), 4)
    return out


def daily_ndvi_mean(composite_means: Mapping[int, float]) -> dict[int, float | None]:
    """Expand composite-start means to every day-of-year 1..366 (`None` where a composite is missing)."""
    return {doy: composite_means.get(composite_doy(doy)) for doy in range(1, 367)}


def ndvi_anomaly(
    current: Mapping[str, float | None], baseline_mean: Mapping[str, float | None]
) -> dict[str, float | None]:
    """`current - baseline_mean` per district; `None` where either side is unavailable (Section 7.6)."""
    return {
        did: None if cur is None or baseline_mean.get(did) is None else round(cur - baseline_mean[did], 4)
        for did, cur in current.items()
    }


def _load_pending(cache_dir: Path) -> dict[str, Any]:
    path = cache_dir / "pending_tasks.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _save_pending(cache_dir: Path, doc: dict[str, Any]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "pending_tasks.json").write_text(json.dumps(doc), encoding="utf-8")


def fetch_current_ndvi(
    districts: Iterable[Mapping[str, Any]] | None = None,
    end: date | None = None,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    max_poll_seconds: float = 20.0,
    poll_interval: float = 5.0,
    cache_dir: Path = MODIS_CACHE_DIR,
    client: httpx.Client | None = None,
) -> tuple[dict[str, float | None], str, dict[str, str | None]]:
    """Latest MOD13Q1.061 NDVI per district, or `None` for every district if unavailable.

    Returns `(values, product_label, composite_dates)`; the composite date (`YYYY-MM-DD`, the start
    of the 16-day period) lets the caller look up the baseline mean for the same period. AppEEARS point tasks are asynchronous and routinely
    take much longer than one request-response cycle to finish (observed: still `pending`
    after 60+ seconds for 8 points, see `docs/data_sources.md`). This function submits a task
    once per date window (reusing a task already pending from an earlier call, tracked in
    `pending_tasks.json`), polls for up to `max_poll_seconds`, and gives up gracefully if the
    task has not finished. Callers must treat `None` as the normal, documented fallback
    (Section 7.6, F2.2), not as an error.
    """
    districts = list(districts) if districts is not None else load_districts()
    none_result = {d["id"]: None for d in districts}
    no_dates: dict[str, str | None] = {d["id"]: None for d in districts}
    end = end or date.today()
    start = end - timedelta(days=window_days)
    cache_key = f"{start.isoformat()}_{end.isoformat()}"
    cache_file = cache_dir / f"{cache_key}.json"
    if cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        return (
            {d["id"]: cached.get("values", {}).get(d["id"]) for d in districts},
            cached.get("product", PRODUCT),
            {d["id"]: cached.get("dates", {}).get(d["id"]) for d in districts},
        )

    try:
        ensure_online("AppEEARS NDVI")
    except Exception:
        return none_result, PRODUCT, no_dates

    owns_client = client is None
    client = client or httpx.Client(timeout=60.0)
    try:
        token = login(client)
        pending = _load_pending(cache_dir)
        entry = pending.get(cache_key)
        if entry is None:
            try:
                task_id = submit_task(districts, start, end, token, client=client)
                product, layer = PRODUCT, LAYER
            except ModisError:
                task_id = submit_task(
                    districts, start, end, token, client=client,
                    product=FALLBACK_PRODUCT, layer=FALLBACK_LAYER,
                )
                product, layer = FALLBACK_PRODUCT, FALLBACK_LAYER
            entry = {"task_id": task_id, "product": product, "layer": layer}
            pending[cache_key] = entry
            _save_pending(cache_dir, pending)
        task_id, product, layer = entry["task_id"], entry["product"], entry["layer"]

        deadline = time.monotonic() + max_poll_seconds
        status = "pending"
        while True:
            status = task_status(task_id, token, client=client)
            if status == "done" or time.monotonic() >= deadline:
                break
            time.sleep(poll_interval)

        if status != "done":
            return none_result, product, no_dates  # still queued on NASA's side; try again next run

        rows = download_point_csv(task_id, token, client=client)
        current = latest_ndvi_readings(rows, product, layer)
        result = {d["id"]: (current[d["id"]][1] if d["id"] in current else None) for d in districts}
        dates = {d["id"]: (current[d["id"]][0] if d["id"] in current else None) for d in districts}

        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps({"product": product, "values": result, "dates": dates}), encoding="utf-8"
        )
        pending.pop(cache_key, None)
        _save_pending(cache_dir, pending)
        return result, product, dates
    except ModisError:
        return none_result, PRODUCT, no_dates
    finally:
        if owns_client:
            client.close()


def main(argv: list[str] | None = None) -> int:
    """CLI: submit/poll/print the current NDVI per district (manual, slow; see module docstring)."""
    import argparse

    parser = argparse.ArgumentParser(description="AppEEARS MOD13Q1.061 NDVI per district")
    parser.add_argument("--end", type=date.fromisoformat, default=None)
    parser.add_argument("--max-poll-seconds", type=float, default=20.0)
    args = parser.parse_args(argv)
    values, product, dates = fetch_current_ndvi(end=args.end, max_poll_seconds=args.max_poll_seconds)
    print(f"AppEEARS {product}, NDVI (most recent 16-day composite in the window)")
    for did, value in values.items():
        shown = "pending/unavailable" if value is None else f"{value:.4f}  (composite {dates.get(did)})"
        print(f"{did:<12} {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
