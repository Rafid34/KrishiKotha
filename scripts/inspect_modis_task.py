"""Print the real AppEEARS result CSV for a finished task (Phase 10, task 10.3).

Run manually: `.venv/Scripts/python scripts/inspect_modis_task.py <task_id>`
Uses the real client functions so the parsing is checked against live output.
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.services.nasa import modis  # noqa: E402


def main() -> int:
    task_id = sys.argv[1]
    with httpx.Client(timeout=60.0) as client:
        token = modis.login(client)
        print("status:", modis.task_status(task_id, token, client=client))
        rows = modis.download_point_csv(task_id, token, client=client)
        print(f"rows: {len(rows)}")
        print("columns:", list(rows[0].keys()))
        for row in rows[:3]:
            print({k: row[k] for k in ("ID", "Date") if k in row}, {k: v for k, v in row.items() if "NDVI" in k})
        product_layer = modis.PRODUCT, modis.LAYER
        latest = modis.latest_ndvi_by_district(rows, *product_layer)
        print("latest NDVI per district:", {k: round(v, 4) for k, v in latest.items()})
        dates = sorted({r["Date"] for r in rows})
        print("composite dates:", dates)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
