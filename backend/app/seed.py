"""Load districts and crops from data/static into the database (idempotent upsert)."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from .config import STATIC_DIR
from .db import SessionLocal, create_all
from .models import Crop, District

DISTRICT_FIELDS = ("name_en", "name_bn", "division", "lat", "lon", "coastal_distance_km", "upstream_bbox")


def _load(name: str) -> Any:
    return json.loads((STATIC_DIR / name).read_text(encoding="utf-8"))


def seed(session: Session) -> dict[str, int]:
    """Upsert districts and crops; return resulting row counts."""
    for row in _load("districts.json"):
        obj = session.get(District, row["id"]) or District(id=row["id"])
        for field in DISTRICT_FIELDS:
            setattr(obj, field, row.get(field))
        session.add(obj)
    for row in _load("crops.json")["crops"]:
        obj = session.get(Crop, row["id"]) or Crop(id=row["id"])
        obj.name_en, obj.name_bn, obj.stages = row["name_en"], row["name_bn"], row["stages"]
        session.add(obj)
    session.commit()
    return {"districts": session.query(District).count(), "crops": session.query(Crop).count()}


def main() -> None:
    """CLI entry point: `python -m backend.app.seed`."""
    create_all()
    with SessionLocal() as session:
        counts = seed(session)
    print(f"Seeded: {counts}")


if __name__ == "__main__":
    main()
