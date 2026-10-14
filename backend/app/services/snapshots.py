"""Export risk rows to JSON snapshots and load them back (offline demo, Section 11.6).

Each snapshot file is self-contained: risk snapshots, the raw observations behind them and
the pipeline run that produced them. Loading never touches the network.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import SNAPSHOT_DIR
from ..models import Observation, PipelineRun, RiskSnapshot
from ..timeutil import iso_utc, parse_iso

FORMAT_VERSION = 1


def snapshot_row_to_dict(row: RiskSnapshot) -> dict[str, Any]:
    """Serialise one `risk_snapshots` row."""
    return {
        "district_id": row.district_id,
        "date": row.date.isoformat(),
        "drought_score": row.drought_score,
        "flood_score": row.flood_score,
        "salt_score": row.salt_score,
        "drought_level": row.drought_level,
        "flood_level": row.flood_level,
        "salt_level": row.salt_level,
        "inputs": row.inputs,
        "sources": row.sources,
        "degraded": bool(row.degraded),
        "created_at": iso_utc(row.created_at),
    }


def observation_to_dict(row: Observation) -> dict[str, Any]:
    """Serialise one `observations` row."""
    return {
        "district_id": row.district_id,
        "date": row.date.isoformat(),
        "source": row.source,
        "variable": row.variable,
        "value": row.value,
        "product_version": row.product_version,
    }


def run_to_dict(run: PipelineRun) -> dict[str, Any]:
    """Serialise one `pipeline_runs` row."""
    return {
        "started_at": iso_utc(run.started_at),
        "finished_at": iso_utc(run.finished_at),
        "status": run.status,
        "detail": run.detail,
    }


def _run_overlaps(run: PipelineRun, first: date, last: date) -> bool:
    detail = run.detail or {}
    try:
        start, end = date.fromisoformat(detail["start"]), date.fromisoformat(detail["end"])
    except (KeyError, TypeError, ValueError):
        return False
    return start <= last and end >= first


def build_snapshot_doc(
    session: Session,
    kind: str,
    start: date,
    end: date,
    district_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Collect rows for `[start, end]` (and optional districts) into a snapshot document."""
    snap_q = select(RiskSnapshot).where(RiskSnapshot.date >= start, RiskSnapshot.date <= end)
    obs_q = select(Observation).where(Observation.date >= start, Observation.date <= end)
    ids = sorted(district_ids) if district_ids else None
    if ids:
        snap_q = snap_q.where(RiskSnapshot.district_id.in_(ids))
        obs_q = obs_q.where(Observation.district_id.in_(ids))
    snaps = session.scalars(snap_q.order_by(RiskSnapshot.date, RiskSnapshot.district_id)).all()
    obs = session.scalars(
        obs_q.order_by(Observation.date, Observation.district_id, Observation.source, Observation.variable)
    ).all()
    runs = [
        r
        for r in session.scalars(select(PipelineRun).order_by(PipelineRun.started_at)).all()
        if _run_overlaps(r, start, end) and r.status in ("ok", "partial")
    ]
    run = runs[-1] if runs else None
    return {
        "format_version": FORMAT_VERSION,
        "kind": kind,
        "generated_at": iso_utc(datetime.now(timezone.utc)),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "district_ids": ids or sorted({s.district_id for s in snaps}),
        "pipeline_run": run_to_dict(run) if run else None,
        "risk_snapshots": [snapshot_row_to_dict(s) for s in snaps],
        "observations": [observation_to_dict(o) for o in obs],
    }


def write_snapshot_doc(doc: dict[str, Any], path: Path) -> Path:
    """Write a snapshot document as UTF-8 JSON and return the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return path


def load_snapshot_doc(session: Session, doc: dict[str, Any]) -> dict[str, int]:
    """Upsert one snapshot document into the database; return counts of rows written."""
    if doc.get("format_version") != FORMAT_VERSION:
        raise ValueError(f"unsupported snapshot format_version {doc.get('format_version')!r}")

    existing = {(s.district_id, s.date): s for s in session.scalars(select(RiskSnapshot)).all()}
    for item in doc["risk_snapshots"]:
        key = (item["district_id"], date.fromisoformat(item["date"]))
        obj = existing.get(key) or RiskSnapshot(district_id=key[0], date=key[1])
        for field in (
            "drought_score", "flood_score", "salt_score",
            "drought_level", "flood_level", "salt_level",
            "inputs", "sources", "degraded",
        ):
            setattr(obj, field, item[field])
        if item.get("created_at"):
            obj.created_at = parse_iso(item["created_at"])
        session.add(obj)
        existing[key] = obj

    seen_obs = {
        (o.district_id, o.date, o.source, o.variable): o
        for o in session.scalars(select(Observation)).all()
    }
    for item in doc["observations"]:
        okey = (item["district_id"], date.fromisoformat(item["date"]), item["source"], item["variable"])
        obs = seen_obs.get(okey) or Observation(
            district_id=okey[0], date=okey[1], source=okey[2], variable=okey[3]
        )
        obs.value = item["value"]
        obs.product_version = item.get("product_version", "")
        session.add(obs)
        seen_obs[okey] = obs

    runs_loaded = 0
    run = doc.get("pipeline_run")
    if run:
        started = parse_iso(run["started_at"])
        if session.scalar(select(PipelineRun).where(PipelineRun.started_at == started)) is None:
            session.add(
                PipelineRun(
                    started_at=started,
                    finished_at=parse_iso(run["finished_at"]) if run.get("finished_at") else None,
                    status=run["status"],
                    detail=run["detail"],
                )
            )
            runs_loaded = 1
    session.commit()
    return {
        "risk_snapshots": len(doc["risk_snapshots"]),
        "observations": len(doc["observations"]),
        "pipeline_runs": runs_loaded,
    }


def load_snapshots(session: Session, directory: Path = SNAPSHOT_DIR) -> dict[str, int]:
    """Load every `*.json` snapshot in `directory`; returns summed counts (zeros if none)."""
    totals = {"files": 0, "risk_snapshots": 0, "observations": 0, "pipeline_runs": 0}
    for path in sorted(directory.glob("*.json")):
        counts = load_snapshot_doc(session, json.loads(path.read_text(encoding="utf-8")))
        totals["files"] += 1
        for key, value in counts.items():
            totals[key] += value
    return totals
