"""CLI: export DB risk rows to data/snapshots/latest_30d.json and sylhet_2022.json."""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import func, select

from backend.app.config import SNAPSHOT_DIR
from backend.app.db import SessionLocal, create_all
from backend.app.models import RiskSnapshot
from backend.app.services.snapshots import build_snapshot_doc, write_snapshot_doc

LATEST_DAYS = 30
SYLHET_START = date(2022, 5, 15)
SYLHET_END = date(2022, 6, 30)


def main(argv: list[str] | None = None) -> int:
    """Write both snapshot files; returns 1 if either has no rows to export."""
    parser = argparse.ArgumentParser(description="Export risk snapshots for the offline demo")
    parser.add_argument("--out", type=Path, default=SNAPSHOT_DIR, help="output directory")
    args = parser.parse_args(argv)

    create_all()
    failed = False
    with SessionLocal() as session:
        newest = session.scalar(select(func.max(RiskSnapshot.date)))
        plans = []
        if newest is not None:
            plans.append(("latest_30d", newest - timedelta(days=LATEST_DAYS - 1), newest, None))
        else:
            print("latest_30d: database has no risk rows", file=sys.stderr)
            failed = True
        # Named for the event, but holds all districts so the replay can also colour the whole map.
        plans.append(("sylhet_2022", SYLHET_START, SYLHET_END, None))

        for kind, start, end, districts in plans:
            doc = build_snapshot_doc(session, kind, start, end, districts)
            if not doc["risk_snapshots"]:
                print(f"{kind}: no rows between {start} and {end}", file=sys.stderr)
                failed = True
                continue
            path = write_snapshot_doc(doc, args.out / f"{kind}.json")
            print(
                f"{kind}: {len(doc['risk_snapshots'])} risk rows, "
                f"{len(doc['observations'])} observations, {start} to {end} -> {path} "
                f"({path.stat().st_size / 1024:.0f} KB)"
            )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
