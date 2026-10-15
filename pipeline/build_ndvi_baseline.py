"""CLI: build the MODIS NDVI 2003-2020 climatology (`ndvi_mean`) for every district (Phase 10, task 10.3).

    python -m pipeline.build_ndvi_baseline [--max-poll-seconds 60]

Submits (or resumes) one AppEEARS point task for MOD13Q1.061 `_250m_16_days_NDVI` over
2003-01-01 to 2020-12-31 at the 8 district centroids, then writes `ndvi_mean` into every
`data/baseline/{district}.json` row and the `baselines` table.

AppEEARS queues tasks on NASA's side (about 20 minutes for a 45-day request on 2026-10-15), so
this command returns exit code 2 with the task id when the task is still pending. Run it again
later; the task id is remembered in `data/cache/modis/pending_tasks.json`. Until it succeeds, the
pipeline has no NDVI anomaly and uses the documented Level 1 salinity formula.
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date

import httpx

from backend.app.db import SessionLocal, create_all
from backend.app.models import Baseline, District
from backend.app.seed import seed
from backend.app.services.nasa import modis
from backend.app.services.risk.baseline import baseline_path, write_ndvi_mean

PENDING_KEY = "baseline_2003_2020"


def _task(client: httpx.Client, token: str, districts: list[dict]) -> dict:
    pending = modis._load_pending(modis.MODIS_CACHE_DIR)
    entry = pending.get(PENDING_KEY)
    if entry is None:
        task_id = modis.submit_task(
            districts, date(modis.BASELINE_START_YEAR, 1, 1), date(modis.BASELINE_END_YEAR, 12, 31),
            token, client=client, task_name="krishi_kotha_ndvi_baseline_2003_2020",
        )
        entry = {"task_id": task_id, "product": modis.PRODUCT, "layer": modis.LAYER}
        pending[PENDING_KEY] = entry
        modis._save_pending(modis.MODIS_CACHE_DIR, pending)
    return entry


def main(argv: list[str] | None = None) -> int:
    """Build the NDVI baseline; 0 = written, 2 = AppEEARS task still pending, 1 = error."""
    parser = argparse.ArgumentParser(description="MODIS NDVI 2003-2020 baseline")
    parser.add_argument("--max-poll-seconds", type=float, default=60.0)
    args = parser.parse_args(argv)

    create_all()
    with SessionLocal() as session:
        seed(session)
        districts = [
            {"id": d.id, "lat": d.lat, "lon": d.lon}
            for d in session.query(District).order_by(District.id).all()
        ]
    missing = [d["id"] for d in districts if not baseline_path(d["id"]).exists()]
    if missing:
        print(f"POWER baselines missing for {missing}; run `python -m pipeline.build_baseline` first.", file=sys.stderr)
        return 1

    with httpx.Client(timeout=120.0) as client:
        try:
            token = modis.login(client)
            entry = _task(client, token, districts)
            deadline = time.monotonic() + args.max_poll_seconds
            while True:
                status = modis.task_status(entry["task_id"], token, client=client)
                if status == "done" or time.monotonic() >= deadline:
                    break
                time.sleep(10)
            if status != "done":
                print(f"AppEEARS task {entry['task_id']} is still '{status}'. Run this command again later.")
                return 2
            rows = modis.download_point_csv(entry["task_id"], token, client=client)
        except modis.ModisError as exc:
            print(f"AppEEARS error: {exc}", file=sys.stderr)
            return 1

    per_district = modis.build_ndvi_baseline(rows, entry["product"], entry["layer"])
    with SessionLocal() as session:
        for d in districts:
            composite_means = per_district.get(d["id"])
            if not composite_means:
                print(f"{d['id']}: no valid NDVI rows, baseline not written", file=sys.stderr)
                continue
            daily = modis.daily_ndvi_mean(composite_means)
            path = write_ndvi_mean(d["id"], daily)
            for doy, value in daily.items():
                row = session.get(Baseline, (d["id"], doy))
                if row is not None:
                    row.ndvi_mean = value
            print(f"{d['id']}: {len(composite_means)} composite means -> {path}")
        session.commit()

    pending = modis._load_pending(modis.MODIS_CACHE_DIR)
    pending.pop(PENDING_KEY, None)
    modis._save_pending(modis.MODIS_CACHE_DIR, pending)
    return 0


if __name__ == "__main__":
    sys.exit(main())
