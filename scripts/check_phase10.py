"""Phase 10 verification: print soil source, NDVI status and pipeline detail for a recent date.

Run after `python -m pipeline.run_pipeline --run late ...`:
    .venv/Scripts/python scripts/check_phase10.py [YYYY-MM-DD]
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from backend.app.db import SessionLocal  # noqa: E402
from backend.app.models import PipelineRun, RiskSnapshot  # noqa: E402


def main() -> int:
    with SessionLocal() as db:
        day = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else db.scalar(
            select(RiskSnapshot.date).order_by(RiskSnapshot.date.desc()).limit(1)
        )
        rows = db.scalars(select(RiskSnapshot).where(RiskSnapshot.date == day).order_by(RiskSnapshot.district_id)).all()
        print(f"Date {day}: {len(rows)} districts")
        for r in rows:
            soil = next(i for i in r.inputs["flood"]["inputs"] if i["name"] == "soil_pctl")
            print(
                f"{r.district_id:<11} soil_source={r.inputs['soil_source']:<15} soil_pctl={soil['value']} "
                f"source={soil['source']!r} flood={r.flood_score} drought={r.drought_score} "
                f"ndvi_anom={r.inputs['ndvi_anom']} degraded={r.degraded}"
            )
        run = db.scalars(select(PipelineRun).order_by(PipelineRun.id.desc()).limit(1)).first()
        print("\nLatest run:", run.status)
        for name in ("SMAP", "MODIS"):
            print(name, json.dumps(run.detail["sources"][name], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
