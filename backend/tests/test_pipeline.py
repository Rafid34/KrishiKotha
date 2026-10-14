"""Pipeline runner, snapshot export/load and the snapshot-mode network guard (no network)."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import get_settings
from backend.app.models import Observation, PipelineRun, RiskSnapshot
from backend.app.services.nasa.offline import OfflineModeError
from backend.app.services.nasa.power import fetch_power
from backend.app.services.snapshots import build_snapshot_doc, load_snapshot_doc
from pipeline.run_pipeline import MAX_SOIL_AGE_DAYS, power_indicators, rain_sums, run_pipeline

START, END = date(2022, 6, 14), date(2022, 6, 16)


def _power_frame(first: date, last: date, soil: float = 0.9, tmax: float = 33.0) -> pd.DataFrame:
    index = pd.date_range(first, last, freq="D", name="date")
    return pd.DataFrame({"GWETROOT": soil, "T2M_MAX": tmax}, index=index)


def _power(lat: float, lon: float, start: date, end: date) -> pd.DataFrame:
    return _power_frame(start, end)


def _rain(mm: float):
    def fetch(day: date, districts: list[dict], run: str) -> dict[str, float | None]:
        return {d["id"]: mm for d in districts}

    return fetch


def test_rain_sums_and_missing_days() -> None:
    daily = {date(2022, 6, 16) - timedelta(days=i): 2.0 for i in range(30)}
    assert rain_sums(daily, date(2022, 6, 16)) == {3: 6.0, 7: 14.0, 30: 60.0}
    daily[date(2022, 6, 1)] = None
    sums = rain_sums(daily, date(2022, 6, 16))
    assert sums[3] == 6.0 and sums[30] is None


def test_power_indicators_stale_soil_and_tmax_window() -> None:
    frame = _power_frame(date(2022, 6, 1), date(2022, 6, 16))
    frame.loc["2022-06-15":, "GWETROOT"] = float("nan")
    frame.loc["2022-06-10", "T2M_MAX"] = 40.0
    got = power_indicators(frame, date(2022, 6, 16))
    assert got.soil == 0.9 and got.soil_date == date(2022, 6, 14) and got.soil_stale_days == 2
    assert got.today_soil is None and got.today_tmax == 33.0
    assert got.tmax7 == pytest.approx((40.0 + 33.0 * 6) / 7)
    empty = power_indicators(frame.iloc[0:0], date(2022, 6, 16))
    assert empty.soil is None and empty.tmax7 is None


def test_power_soil_max_age_boundary() -> None:
    frame = _power_frame(date(2022, 6, 1), date(2022, 6, 16))
    frame.loc["2022-06-10":, "GWETROOT"] = float("nan")  # last soil value is 2022-06-09
    at_limit = power_indicators(frame, date(2022, 6, 16))  # exactly 7 days old
    assert at_limit.soil == 0.9 and at_limit.soil_stale_days == MAX_SOIL_AGE_DAYS == 7
    expired = power_indicators(frame, date(2022, 6, 17))  # 8 days old
    assert expired.soil is None and expired.soil_date is None
    assert expired.soil_stale_days == 8  # age of the expired value is still recorded
    assert expired.tmax7 == 33.0  # Tmax handling is unchanged


def test_expired_soil_triggers_degraded_fallback(session_factory: sessionmaker[Session]) -> None:
    def old_soil(lat: float, lon: float, start: date, end: date) -> pd.DataFrame:
        frame = _power_frame(start, end)
        frame.loc[pd.Timestamp(END - timedelta(days=8)) :, "GWETROOT"] = float("nan")  # last value 2022-06-07
        return frame

    with session_factory() as db:
        record = run_pipeline(db, START, END, "late", rain_fetcher=_rain(5.0), power_fetcher=old_soil)
        assert record.status == "ok"

        def sylhet_on(day: date) -> RiskSnapshot:
            return db.scalars(
                select(RiskSnapshot).where(RiskSnapshot.district_id == "sylhet", RiskSnapshot.date == day)
            ).one()

        fresh = sylhet_on(START)  # soil is 7 days old: still usable
        assert fresh.degraded is False and fresh.inputs["soil_stale_days"] == 7
        expired = sylhet_on(END)  # soil is 9 days old: counts as missing
        assert expired.degraded is True
        assert expired.inputs["soil_wetness"] is None and expired.inputs["soil_stale_days"] == 9
        assert expired.inputs["soil_missing"] is True  # Section 7.6: expired soil sets soil_missing
        soil_input = next(i for i in expired.inputs["flood"]["inputs"] if i["name"] == "soil_pctl")
        assert soil_input["value"] is None and soil_input["weight"] == 0.0


def test_run_pipeline_writes_scores_observations_and_run(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as db:
        record = run_pipeline(db, START, END, "final", rain_fetcher=_rain(120.0), power_fetcher=_power)
        assert record.status == "ok"
        assert record.detail["snapshots_written"] == 24
        assert record.detail["sources"]["IMERG"]["status"] == "ok"
        assert record.detail["sources"]["POWER"]["last_data_date"] == "2022-06-16"

        rows = db.scalars(select(RiskSnapshot).where(RiskSnapshot.date == END)).all()
        assert len(rows) == 8
        sylhet = next(r for r in rows if r.district_id == "sylhet")
        assert sylhet.flood_level == "high" and sylhet.degraded is False
        assert 0.0 <= sylhet.drought_score <= 100.0
        flood_inputs = sylhet.inputs["flood"]["inputs"]
        assert {"source", "data_date"} <= set(flood_inputs[0])
        assert sylhet.sources["rain"]["short_name"] == "GPM_3IMERGDF"

        sources = {(o.source, o.variable) for o in db.scalars(select(Observation))}
        assert sources == {("IMERG_FINAL", "precip_mm"), ("POWER", "tmax_c"), ("POWER", "soil_wetness")}

        run_pipeline(db, START, END, "final", rain_fetcher=_rain(120.0), power_fetcher=_power)
        assert db.scalar(select(func.count()).select_from(RiskSnapshot)) == 24  # upsert, no duplicates
        assert db.scalar(select(func.count()).select_from(PipelineRun)) == 2


def test_missing_soil_marks_degraded(session_factory: sessionmaker[Session]) -> None:
    def no_soil(lat: float, lon: float, start: date, end: date) -> pd.DataFrame:
        frame = _power_frame(start, end)
        frame["GWETROOT"] = float("nan")
        return frame

    with session_factory() as db:
        record = run_pipeline(db, END, END, "late", rain_fetcher=_rain(5.0), power_fetcher=no_soil)
        assert record.status == "ok"
        row = db.scalars(select(RiskSnapshot)).first()
        assert row is not None and row.degraded is True
        # Section 7.6: missing soil sets inputs.soil_missing
        assert row.inputs["soil_missing"] is True


def test_failed_imerg_day_skips_incomplete_windows(session_factory: sessionmaker[Session]) -> None:
    bad_day = END - timedelta(days=1)

    def flaky(day: date, districts: list[dict], run: str) -> dict[str, float | None]:
        if day == bad_day:
            raise RuntimeError("granule missing")
        return {d["id"]: 3.0 for d in districts}

    with session_factory() as db:
        record = run_pipeline(
            db, END, END, "late", rain_fetcher=flaky, power_fetcher=_power, sleep=lambda _: None
        )
        assert record.status == "failed"  # every window includes the missing day: nothing scored
        assert record.detail["sources"]["IMERG"]["failed_days"] == {bad_day.isoformat(): "RuntimeError: granule missing"}
        assert db.scalar(select(func.count()).select_from(RiskSnapshot)) == 0


def test_failed_power_district_gives_partial_status(session_factory: sessionmaker[Session]) -> None:
    def power(lat: float, lon: float, start: date, end: date) -> pd.DataFrame:
        if abs(lat - 24.8949) < 1e-6:  # Sylhet
            raise RuntimeError("POWER down")
        return _power_frame(start, end)

    with session_factory() as db:
        record = run_pipeline(db, END, END, "late", rain_fetcher=_rain(5.0), power_fetcher=power)
        assert record.status == "partial"
        assert list(record.detail["sources"]["POWER"]["failed_districts"]) == ["sylhet"]
        assert db.scalar(select(func.count()).select_from(RiskSnapshot)) == 7


def test_snapshot_export_and_reload_round_trip(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as db:
        run_pipeline(db, START, END, "final", rain_fetcher=_rain(80.0), power_fetcher=_power)
        doc = build_snapshot_doc(db, "sylhet_2022", START, END, ["sylhet"])
        original = db.scalars(select(RiskSnapshot).where(RiskSnapshot.district_id == "sylhet", RiskSnapshot.date == END)).one()
        expected = (original.flood_score, original.inputs)
    assert len(doc["risk_snapshots"]) == 3 and doc["pipeline_run"]["status"] == "ok"

    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    from backend.app.db import Base

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as fresh:
        counts = load_snapshot_doc(fresh, doc)
        assert counts["risk_snapshots"] == 3 and counts["pipeline_runs"] == 1
        loaded = fresh.scalars(select(RiskSnapshot).where(RiskSnapshot.date == END)).one()
        assert (loaded.flood_score, loaded.inputs) == expected
        assert load_snapshot_doc(fresh, doc)["pipeline_runs"] == 0  # idempotent
        assert fresh.scalar(select(func.count()).select_from(RiskSnapshot)) == 3


def test_snapshot_mode_blocks_network_clients(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_MODE", "snapshot")
    get_settings.cache_clear()
    try:
        with pytest.raises(OfflineModeError):
            fetch_power(24.9, 91.9, date(2022, 6, 1), date(2022, 6, 2), cache_dir=tmp_path)
    finally:
        monkeypatch.setenv("DATA_MODE", "live")
        get_settings.cache_clear()
