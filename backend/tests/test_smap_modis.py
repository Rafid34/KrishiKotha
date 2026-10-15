"""SMAP L4 reader and AppEEARS NDVI client (no network: synthetic HDF5 and mocked HTTP)."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import h5py
import httpx
import numpy as np
import pytest

from backend.app.services.nasa import modis, smap

DISTRICTS = [
    {"id": "a", "lat": 24.9, "lon": 91.9},
    {"id": "b", "lat": 22.8, "lon": 89.5},
    {"id": "c", "lat": 25.7, "lon": 89.3},
]


def _write_smap(path: Path) -> None:
    """Tiny file in the real layout: Geophysical_Data/sm_rootzone_pctl plus 2-D cell_lat/cell_lon."""
    lats = np.linspace(27.0, 20.0, 15, dtype="float32")  # rows run north to south, as in EASE-Grid 2.0
    lons = np.linspace(88.0, 93.0, 21, dtype="float32")
    cell_lat = np.repeat(lats[:, None], lons.size, axis=1)
    cell_lon = np.repeat(lons[None, :], lats.size, axis=0)
    grid = np.full(cell_lat.shape, 50.0, dtype="float32")
    row_a, col_a = int(np.argmin(abs(lats - 24.9))), int(np.argmin(abs(lons - 91.9)))
    row_b, col_b = int(np.argmin(abs(lats - 22.8))), int(np.argmin(abs(lons - 89.5)))
    grid[row_a, col_a] = 98.5
    grid[row_b, col_b] = -9999.0  # water cell: fill value
    with h5py.File(path, "w") as f:
        f.create_group("Geophysical_Data").create_dataset("sm_rootzone_pctl", data=grid)
        f.create_dataset("cell_lat", data=cell_lat)
        f.create_dataset("cell_lon", data=cell_lon)


def test_read_district_values_nearest_cell_and_fill(tmp_path: Path) -> None:
    path = tmp_path / "smap.h5"
    _write_smap(path)
    values = smap.read_district_values(path, DISTRICTS)
    assert values["a"] == pytest.approx(98.5)
    assert values["b"] is None  # fill value becomes null
    assert values["c"] == pytest.approx(50.0)


def test_district_values_uses_cache_without_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    day = date(2022, 6, 16)
    smap.cache_path(day, tmp_path).write_text(json.dumps({"a": 12.5, "b": None}), encoding="utf-8")

    def boom(*a, **k):  # any download attempt fails the test
        raise AssertionError("network used despite cache")

    monkeypatch.setattr(smap, "fetch_granule", boom)
    got = smap.district_values(day, DISTRICTS, cache_dir=tmp_path)
    assert got == {"a": 12.5, "b": None, "c": None}


def test_district_values_downloads_reads_caches_and_deletes_raw(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw = raw_dir / "granule.h5"
    _write_smap(raw)
    monkeypatch.setattr(smap, "fetch_granule", lambda day: raw)
    cache = tmp_path / "cache"
    got = smap.district_values(date(2026, 10, 10), DISTRICTS, cache_dir=cache)
    assert got["a"] == pytest.approx(98.5)
    assert not raw_dir.exists()  # raw granule directory deleted
    assert json.loads(smap.cache_path(date(2026, 10, 10), cache).read_text())["a"] == pytest.approx(98.5)


# --- MODIS / AppEEARS -----------------------------------------------------------------------

CSV = (
    "ID,Date,MOD13Q1_061__250m_16_days_NDVI\n"
    "a,2026-09-30,0.6\na,2026-10-16,0.7\nb,2026-09-30,0.5\nb,2026-10-16,-0.3\nc,2026-10-16,\n"
)


def _client(status: str, calls: list[str]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        path = request.url.path
        if path.endswith("/login"):
            return httpx.Response(200, json={"token": "tok"})
        if path.endswith("/task"):
            return httpx.Response(202, json={"task_id": "t1", "status": "pending"})
        if path.endswith("/status/t1"):
            # Real behaviour: a finished task answers 303 with the status in the body.
            code = 303 if status == "done" else 200
            return httpx.Response(code, json={"status": status}, headers={"location": "/api/task/t1"} if code == 303 else {})
        if path.endswith("/bundle/t1"):
            return httpx.Response(200, json={"files": [{"file_name": "x-results.csv", "file_id": "f1"}]})
        if path.endswith("/bundle/t1/f1"):
            return httpx.Response(200, content=CSV.encode())
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture()
def creds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        modis, "get_settings", lambda: SimpleNamespace(earthdata_username="u", earthdata_password="p")
    )


def test_latest_ndvi_uses_scaled_values_and_skips_fill_and_blank() -> None:
    rows = list(__import__("csv").DictReader(CSV.splitlines()))
    got = modis.latest_ndvi_by_district(rows)
    # b's newest row is the -0.3 fill value, so its earlier valid composite is used; c has only a blank.
    assert got == {"a": pytest.approx(0.7), "b": pytest.approx(0.5)}


def test_ndvi_anomaly_requires_both_sides() -> None:
    out = modis.ndvi_anomaly({"a": 0.6, "b": None, "c": 0.5}, {"a": 0.7, "b": 0.7, "c": None})
    assert out == {"a": pytest.approx(-0.1), "b": None, "c": None}


def test_fetch_current_ndvi_done_caches_and_clears_pending(tmp_path: Path, creds: None) -> None:
    calls: list[str] = []
    values, product, dates = modis.fetch_current_ndvi(
        DISTRICTS, date(2026, 10, 15), max_poll_seconds=0, cache_dir=tmp_path, client=_client("done", calls)
    )
    assert product == "MOD13Q1.061"
    assert dates == {"a": "2026-10-16", "b": "2026-09-30", "c": None}
    assert values == {"a": pytest.approx(0.7), "b": pytest.approx(0.5), "c": None}
    assert json.loads((tmp_path / "pending_tasks.json").read_text()) == {}
    # Second call is served from the cache with no HTTP traffic.
    calls.clear()
    again, _, again_dates = modis.fetch_current_ndvi(
        DISTRICTS, date(2026, 10, 15), cache_dir=tmp_path, client=_client("done", calls)
    )
    assert again["a"] == pytest.approx(0.7) and calls == [] and again_dates["a"] == "2026-10-16"


def test_fetch_current_ndvi_pending_returns_none_and_remembers_task(tmp_path: Path, creds: None) -> None:
    calls: list[str] = []
    values, _, dates = modis.fetch_current_ndvi(
        DISTRICTS, date(2026, 10, 15), max_poll_seconds=0, cache_dir=tmp_path, client=_client("pending", calls)
    )
    assert values == {"a": None, "b": None, "c": None} and dates == values
    pending = json.loads((tmp_path / "pending_tasks.json").read_text())
    assert list(pending.values())[0]["task_id"] == "t1"
    # A second call reuses the pending task instead of submitting another one.
    calls.clear()
    modis.fetch_current_ndvi(
        DISTRICTS, date(2026, 10, 15), max_poll_seconds=0, cache_dir=tmp_path, client=_client("pending", calls)
    )
    assert "POST /task" not in " ".join(calls) and not any(c.endswith("/task") for c in calls)


def test_fetch_current_ndvi_login_failure_falls_back(tmp_path: Path, creds: None) -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401)))
    values, _, _ = modis.fetch_current_ndvi(DISTRICTS, date(2026, 10, 15), cache_dir=tmp_path, client=client)
    assert values == {"a": None, "b": None, "c": None}


def test_task_status_handles_real_response_shapes() -> None:
    bodies = {
        "pending": (200, {"task_id": "t", "status": "pending"}),
        "processing": (200, {"task_id": "t", "progress": {"details": []}}),  # no `status` key
        "done": (303, {"task_id": "t", "status": "done"}),
    }
    for expected, (code, body) in bodies.items():
        client = httpx.Client(transport=httpx.MockTransport(lambda r, c=code, b=body: httpx.Response(c, json=b)))
        assert modis.task_status("t", "tok", client=client) == expected
    bad = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    with pytest.raises(modis.ModisError):
        modis.task_status("t", "tok", client=bad)


def test_composite_doy_and_daily_expansion() -> None:
    assert [modis.composite_doy(d) for d in (1, 16, 17, 257, 264, 353, 365, 366)] == [1, 1, 17, 257, 257, 353, 353, 353]
    daily = modis.daily_ndvi_mean({257: 0.61, 273: 0.58})
    assert daily[260] == 0.61 and daily[273] == 0.58 and daily[1] is None and len(daily) == 366


def test_build_ndvi_baseline_averages_same_composite_over_baseline_years() -> None:
    csv_text = (
        "ID,Date,MOD13Q1_061__250m_16_days_NDVI\n"
        "a,2002-09-14,0.10\n"   # before 2003: excluded
        "a,2003-09-14,0.60\na,2004-09-13,0.70\n"  # leap year: same day-of-year 257 only in non-leap years
        "a,2021-09-14,0.10\n"   # after 2020: excluded
        "a,2005-09-14,-0.30\n"  # fill value: excluded
        "b,2003-01-01,0.40\n"
    )
    rows = list(__import__("csv").DictReader(csv_text.splitlines()))
    out = modis.build_ndvi_baseline(rows)
    # 2003-09-14 is doy 257; 2004-09-13 is doy 257 as well (leap year), so both average together.
    assert out["a"] == {257: pytest.approx(0.65)}
    assert out["b"] == {1: pytest.approx(0.40)}


def test_write_ndvi_mean_and_merge_keep_other_baseline_fields(tmp_path: Path) -> None:
    from backend.app.services.risk import baseline as bl

    rows = {d: {"rain3_sorted": [1.0], "rain7_sorted": [2.0], "rain30_mean": 3.0, "tmax_mean": 30.0, "soil_sorted": [0.5]} for d in range(1, 367)}
    bl.write_baseline_file("a", rows, 2001, 2020, base_dir=tmp_path)
    bl.write_ndvi_mean("a", modis.daily_ndvi_mean({257: 0.61}), base_dir=tmp_path)
    loaded = bl.load_baseline("a", tmp_path)
    assert loaded[260]["ndvi_mean"] == 0.61 and loaded[1]["ndvi_mean"] is None
    assert loaded[260]["rain30_mean"] == 3.0
    # A rebuilt POWER baseline keeps the NDVI climatology.
    fresh = {d: {**rows[d]} for d in rows}
    merged = bl.merge_ndvi_mean("a", fresh, tmp_path)
    assert merged[260]["ndvi_mean"] == 0.61 and "ndvi_mean" not in merged[1]


def test_fetch_current_ndvi_offline_mode_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.app.config import get_settings

    monkeypatch.setenv("DATA_MODE", "snapshot")
    get_settings.cache_clear()
    try:
        values, _, _ = modis.fetch_current_ndvi(DISTRICTS, date(2026, 10, 15), cache_dir=tmp_path)
    finally:
        monkeypatch.setenv("DATA_MODE", "live")
        get_settings.cache_clear()
    assert values == {"a": None, "b": None, "c": None}
