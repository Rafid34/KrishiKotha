"""Tests for POST /api/admin/pipeline/run (R-002, Task B3)."""
from __future__ import annotations

import threading
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import get_settings
from backend.app.models import PipelineRun
import backend.app.routers.admin as admin_router
from backend.tests.conftest import ADMIN_KEY


def test_pipeline_run_requires_admin_key(client: TestClient) -> None:
    resp = client.post("/api/admin/pipeline/run", json={"mode": "live"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_pipeline_run_snapshot_mode_conflict(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_MODE", "snapshot")
    get_settings.cache_clear()
    try:
        resp = client.post(
            "/api/admin/pipeline/run",
            json={"mode": "live"},
            headers={"X-Admin-Key": ADMIN_KEY},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "conflict"
    finally:
        monkeypatch.setenv("DATA_MODE", "live")
        get_settings.cache_clear()


def test_pipeline_run_already_active_conflict(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as db:
        db.add(PipelineRun(status="running", started_at=datetime.now(timezone.utc)))
        db.commit()

    resp = client.post(
        "/api/admin/pipeline/run",
        json={"mode": "live", "as_of": "2022-06-16", "run": "late"},
        headers={"X-Admin-Key": ADMIN_KEY},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


def test_pipeline_run_success_with_injected_runner(
    client: TestClient, session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    runner_called = threading.Event()
    called_args: dict[str, object] = {}

    def fake_runner(record_id: int, start: date, end: date, run: str, mode: str) -> None:
        called_args["record_id"] = record_id
        called_args["start"] = start
        called_args["end"] = end
        called_args["run"] = run
        called_args["mode"] = mode
        with session_factory() as db:
            record = db.get(PipelineRun, record_id)
            if record:
                record.status = "ok"
                record.finished_at = datetime.now(timezone.utc)
                record.detail = {"snapshots_written": 24}
                db.commit()
        runner_called.set()

    monkeypatch.setattr(admin_router, "pipeline_runner", fake_runner)

    resp = client.post(
        "/api/admin/pipeline/run",
        json={"mode": "live", "as_of": "2022-06-16", "run": "late"},
        headers={"X-Admin-Key": ADMIN_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "started"
    run_id = data["run_id"]

    assert runner_called.wait(timeout=2.0)
    assert called_args["record_id"] == run_id
    assert called_args["end"] == date(2022, 6, 16)
    assert called_args["start"] == date(2022, 5, 18)  # 2022-06-16 minus 29 days
    assert called_args["run"] == "late"
    assert called_args["mode"] == "live"

    with session_factory() as db:
        record = db.get(PipelineRun, run_id)
        assert record is not None
        assert record.status == "ok"
        assert record.finished_at is not None
        assert record.detail["snapshots_written"] == 24


def test_run_pipeline_updates_existing_record_id(
    session_factory: sessionmaker[Session]
) -> None:
    import pandas as pd
    import pipeline.run_pipeline as p_mod

    with session_factory() as db:
        record = PipelineRun(status="running", started_at=datetime.now(timezone.utc))
        db.add(record)
        db.commit()
        db.refresh(record)
        rec_id = record.id

        def fake_rain(day: date, districts: list[dict], run: str) -> dict[str, float | None]:
            return {d["id"]: 5.0 for d in districts}

        def fake_power(lat: float, lon: float, start: date, end: date) -> pd.DataFrame:
            idx = pd.date_range(start, end, freq="D", name="date")
            return pd.DataFrame({"GWETROOT": 0.8, "T2M_MAX": 30.0}, index=idx)

        def fake_smap(day: date, districts: list[dict]) -> dict[str, float | None]:
            return {d["id"]: None for d in districts}

        def fake_ndvi(districts: list[dict], end: date) -> tuple[dict[str, float | None], str, dict[str, str | None]]:
            return {d["id"]: None for d in districts}, "MOD13Q1.061", {d["id"]: None for d in districts}

        updated = p_mod.run_pipeline(
            db,
            date(2022, 6, 16),
            date(2022, 6, 16),
            "late",
            record_id=rec_id,
            rain_fetcher=fake_rain,
            power_fetcher=fake_power,
            soil_fetcher=fake_smap,
            ndvi_fetcher=fake_ndvi,
        )
        assert updated.id == rec_id
        assert updated.status == "ok"
        assert updated.finished_at is not None
