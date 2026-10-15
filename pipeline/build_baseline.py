"""CLI: build data/baseline/*.json and the baselines table from POWER 2001-2020."""
from __future__ import annotations

import sys
from datetime import date

from backend.app.config import get_settings
from backend.app.db import SessionLocal, create_all
from backend.app.models import District
from backend.app.seed import seed
from backend.app.services.nasa.power import fetch_power
from backend.app.services.risk.baseline import (
    compute_baseline,
    merge_ndvi_mean,
    store_baseline_rows,
    write_baseline_file,
)


def main() -> int:
    """Build baselines for every district; return a process exit code."""
    settings = get_settings()
    start = date(settings.baseline_start_year, 1, 1)
    end = date(settings.baseline_end_year, 12, 31)
    create_all()
    failures = 0
    with SessionLocal() as session:
        seed(session)
        for district in session.query(District).order_by(District.id).all():
            try:
                frame = fetch_power(district.lat, district.lon, start, end)
                rows = merge_ndvi_mean(district.id, compute_baseline(frame))
                path = write_baseline_file(
                    district.id, rows, settings.baseline_start_year, settings.baseline_end_year
                )
                store_baseline_rows(session, district.id, rows)
                print(f"{district.id}: {len(frame)} days -> {path}")
            except Exception as exc:  # keep going so one outage does not block the rest
                failures += 1
                print(f"{district.id}: FAILED ({exc})", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
