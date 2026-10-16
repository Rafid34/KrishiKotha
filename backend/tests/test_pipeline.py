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
import pipeline.run_pipeline as pipeline_module
from pipeline.run_pipeline import MAX_SOIL_AGE_DAYS, power_indicators, rain_sums

START, END = date(2022, 6, 14), date(2022, 6, 16)


def _no_smap(day: date, districts: list[dict]) -> dict[str, float | None]:
    return {d["id"]: None for d in districts}


def _no_ndvi(districts: list[dict], end: date) -> tuple[dict[str, float | None], str, dict[str, str | None]]:
    return {d["id"]: None for d in districts}, "MOD13Q1.061", {d["id"]: None for d in districts}


def run_pipeline(*args, **kwargs):
    """Real runner with SMAP and NDVI faked as unavailable unless a test overrides them (no network)."""
    kwargs.setdefault("soil_fetcher", _no_smap)
    kwargs.setdefault("ndvi_fetcher", _no_ndvi)
    return pipeline_module.run_pipeline(*args, **kwargs)


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
        assert sources == {
            ("IMERG_FINAL", "precip_mm"), ("POWER", "tmax_c"), ("POWER", "soil_wetness"),
            ("SMAP_L4", "rz_pctl"),  # stored as null when SMAP is unavailable
        }
        assert sylhet.inputs["soil_source"] == "POWER_GWETROOT"
        assert record.detail["sources"]["SMAP"]["status"] == "unavailable_fallback_to_power"
        assert record.detail["sources"]["MODIS"]["status"] == "unavailable_fallback_no_ndvi"

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


def _sylhet_row(db: Session) -> RiskSnapshot:
    return db.scalars(
        select(RiskSnapshot).where(RiskSnapshot.district_id == "sylhet", RiskSnapshot.date == END)
    ).one()


def test_smap_preferred_over_power_and_source_recorded(session_factory: sessionmaker[Session]) -> None:
    def smap_fetch(day: date, districts: list[dict]) -> dict[str, float | None]:
        return {d["id"]: 97.0 for d in districts}

    with session_factory() as db:
        record = run_pipeline(
            db, END, END, "final", rain_fetcher=_rain(5.0), power_fetcher=_power, soil_fetcher=smap_fetch
        )
        assert record.status == "ok"
        row = _sylhet_row(db)
        assert row.inputs["soil_source"] == "SMAP_L4" and row.degraded is False
        soil = next(i for i in row.inputs["flood"]["inputs"] if i["name"] == "soil_pctl")
        assert soil["value"] == 97.0 and soil["source"].startswith("SMAP L4")
        assert soil["data_date"] == END.isoformat()
        assert row.sources["soil"]["version"] == "008"
        obs = db.scalars(select(Observation).where(Observation.source == "SMAP_L4")).all()
        assert obs and all(o.value == 97.0 and o.variable == "rz_pctl" for o in obs)
        assert record.detail["sources"]["SMAP"]["status"] == "ok"


def test_smap_failure_falls_back_to_power_without_degrading(session_factory: sessionmaker[Session]) -> None:
    def broken(day: date, districts: list[dict]) -> dict[str, float | None]:
        raise RuntimeError("no granule")

    with session_factory() as db:
        record = run_pipeline(
            db, END, END, "late", rain_fetcher=_rain(5.0), power_fetcher=_power, soil_fetcher=broken
        )
        assert record.status == "ok"  # SMAP never affects the overall status (Section 7.7)
        row = _sylhet_row(db)
        assert row.inputs["soil_source"] == "POWER_GWETROOT" and row.degraded is False
        soil = next(i for i in row.inputs["drought"]["inputs"] if i["name"] == "soil_pctl")
        assert soil["source"] == "NASA POWER GWETROOT"
        smap_detail = record.detail["sources"]["SMAP"]
        assert smap_detail["status"] == "unavailable_fallback_to_power"
        assert smap_detail["failed_days"] == {END.isoformat(): "RuntimeError: no granule"}


def test_smap_partial_district_uses_power_for_the_rest(session_factory: sessionmaker[Session]) -> None:
    def partial(day: date, districts: list[dict]) -> dict[str, float | None]:
        return {d["id"]: (50.0 if d["id"] == "sylhet" else None) for d in districts}

    with session_factory() as db:
        run_pipeline(db, END, END, "late", rain_fetcher=_rain(5.0), power_fetcher=_power, soil_fetcher=partial)
        rows = {r.district_id: r for r in db.scalars(select(RiskSnapshot))}
        assert rows["sylhet"].inputs["soil_source"] == "SMAP_L4"
        assert rows["khulna"].inputs["soil_source"] == "POWER_GWETROOT"


def test_ndvi_anomaly_used_when_current_and_baseline_exist(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    real_load = pipeline_module.load_baseline

    def with_ndvi(district_id: str):
        rows = real_load(district_id)
        return {doy: {**row, "ndvi_mean": 0.70} for doy, row in rows.items()}

    monkeypatch.setattr(pipeline_module, "load_baseline", with_ndvi)

    def ndvi(districts: list[dict], end: date):
        return {d["id"]: 0.55 for d in districts}, "MOD13Q1.061", {d["id"]: "2022-03-22" for d in districts}

    with session_factory() as db:
        record = run_pipeline(
            db, date(2022, 4, 10), date(2022, 4, 10), "late",
            rain_fetcher=_rain(0.0), power_fetcher=_power, ndvi_fetcher=ndvi,
        )
        row = db.scalars(
            select(RiskSnapshot).where(RiskSnapshot.district_id == "satkhira")
        ).one()
        assert row.inputs["ndvi_anom"] == pytest.approx(-0.15)
        veg = next(i for i in row.inputs["salt"]["inputs"] if i["name"] == "vegetation_anomaly")
        assert veg["value"] == 100.0 and veg["source"] == "AppEEARS MOD13Q1.061"
        assert row.sources["ndvi"]["version"] == "061" and row.degraded is False
        assert row.sources["ndvi"]["data_date"] == "2022-03-22"  # composite date, not the scored day
        assert record.detail["sources"]["MODIS"]["status"] == "ok"
        assert record.detail["sources"]["MODIS"]["composite_dates"]["satkhira"] == "2022-03-22"


def test_ndvi_without_baseline_uses_level1_salinity_not_degraded(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    real_load = pipeline_module.load_baseline

    def without_ndvi(district_id: str):  # the real files now carry ndvi_mean; strip it for this case
        return {doy: {k: v for k, v in row.items() if k != "ndvi_mean"} for doy, row in real_load(district_id).items()}

    monkeypatch.setattr(pipeline_module, "load_baseline", without_ndvi)

    def ndvi(districts: list[dict], end: date):
        return {d["id"]: 0.55 for d in districts}, "MOD13Q1.061", {d["id"]: "2022-06-10" for d in districts}

    with session_factory() as db:
        record = run_pipeline(
            db, END, END, "late", rain_fetcher=_rain(5.0), power_fetcher=_power, ndvi_fetcher=ndvi
        )
        row = _sylhet_row(db)
        assert row.inputs["ndvi_anom"] is None and row.degraded is False
        assert all(i["name"] != "vegetation_anomaly" for i in row.inputs["salt"]["inputs"])
        assert record.detail["sources"]["MODIS"]["status"] == "ndvi_without_baseline_fallback"
        assert db.scalars(select(Observation).where(Observation.source == "MODIS_MOD13Q1")).first() is not None


def test_snapshot_mode_blocks_network_clients(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_MODE", "snapshot")
    get_settings.cache_clear()
    try:
        with pytest.raises(OfflineModeError):
            fetch_power(24.9, 91.9, date(2022, 6, 1), date(2022, 6, 2), cache_dir=tmp_path)
    finally:
        monkeypatch.setenv("DATA_MODE", "live")
        get_settings.cache_clear()


def test_main_exit_codes(session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline_module, "SessionLocal", session_factory)

    class DummyRecord:
        def __init__(self, status: str):
            self.status = status
            self.detail = {
                "snapshots_written": 16,
                "sources": {
                    "IMERG": {"status": "ok", "last_data_date": "2022-05-16"},
                    "POWER": {"status": "ok", "last_data_date": "2022-05-16"},
                },
            }

    monkeypatch.setattr(pipeline_module, "run_pipeline", lambda *args, **kwargs: DummyRecord("partial"))
    assert pipeline_module.main(["--start", "2022-05-15", "--end", "2022-05-16"]) == 1

    monkeypatch.setattr(pipeline_module, "run_pipeline", lambda *args, **kwargs: DummyRecord("ok"))
    assert pipeline_module.main(["--start", "2022-05-15", "--end", "2022-05-16"]) == 0

