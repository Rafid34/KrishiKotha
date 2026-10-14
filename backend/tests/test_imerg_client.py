"""IMERG client tests on a synthetic 10 x 10 grid laid out like a real granule (no network)."""
from __future__ import annotations

from datetime import date

import numpy as np
import pytest
import xarray as xr

from backend.app.services.nasa import imerg

BBOX = (88.0, 20.5, 92.7, 26.7)


def synthetic_granule(fill_cell: tuple[int, int] | None = None) -> xr.Dataset:
    """10 x 10 grid, dims (time, lon, lat) like the real V07 file; value = 10 * lat_index."""
    lat = np.round(np.arange(24.05, 25.05, 0.1), 2)  # 10 cell centres
    lon = np.round(np.arange(91.05, 92.05, 0.1), 2)
    values = np.repeat((10.0 * np.arange(10))[None, :], 10, axis=0)  # (lon, lat)
    if fill_cell is not None:
        values[fill_cell] = np.nan
    return xr.Dataset(
        {"precipitation": (("time", "lon", "lat"), values[None].astype("float32"))},
        coords={"time": [np.datetime64("2022-06-16")], "lon": lon, "lat": lat},
    )


def test_clip_normalises_dimension_order_and_drops_time() -> None:
    da = imerg.clip_to_bbox(synthetic_granule(), BBOX)
    assert da.dims == ("lat", "lon")
    assert da.shape == (10, 10)
    assert da.sel(lat=24.05).values[0] == 0.0
    assert da.sel(lat=24.95).values[0] == 90.0


def test_clip_restricts_to_bbox_and_masks_negative_fill() -> None:
    ds = synthetic_granule()
    ds["precipitation"][0, 0, 0] = -9999.9
    da = imerg.clip_to_bbox(ds, (91.0, 24.0, 91.5, 24.5))
    assert da.shape == (5, 5)
    assert float(da["lat"].min()) > 24.0 and float(da["lon"].max()) < 91.5
    assert np.isnan(da.isel(lat=0, lon=0).item())


def test_clip_outside_grid_raises() -> None:
    with pytest.raises(imerg.ImergError):
        imerg.clip_to_bbox(synthetic_granule(), (0.0, 0.0, 1.0, 1.0))


def test_box_mean_uses_centroid_plus_minus_quarter_degree() -> None:
    da = imerg.clip_to_bbox(synthetic_granule(), BBOX)
    # lat 24.55 +/- 0.25 covers centres 24.35..24.75 (lat indexes 3..7) -> mean 50
    assert imerg.box_mean(da, 24.55, 91.55) == pytest.approx(50.0)


def test_box_mean_ignores_fill_and_returns_none_when_all_fill() -> None:
    da = imerg.clip_to_bbox(synthetic_granule(), BBOX)
    partial = da.copy()
    partial[{"lat": 5, "lon": 5}] = np.nan
    assert imerg.box_mean(partial, 24.55, 91.55) is not None
    assert imerg.box_mean(da * np.nan, 24.55, 91.55) is None


def test_cache_roundtrip_district_means_and_accumulate(tmp_path) -> None:
    clipped = imerg.clip_to_bbox(synthetic_granule(), BBOX)
    districts = [{"id": "x", "lat": 24.55, "lon": 91.55}]
    for day in (date(2022, 6, 15), date(2022, 6, 16)):
        imerg._write_clipped(clipped, day, imerg.cache_path(day, "final", tmp_path))

    assert imerg.cache_path(date(2022, 6, 16), "final", tmp_path).name == "final_20220616.nc"
    assert imerg.fetch_day(date(2022, 6, 16), "final", cache_dir=tmp_path).exists()  # cache hit, no network
    means = imerg.district_means(date(2022, 6, 16), districts, "final", cache_dir=tmp_path)
    assert means == {"x": pytest.approx(50.0)}

    acc = imerg.accumulate(districts[0], date(2022, 6, 16), 3, "final", cache_dir=tmp_path)
    assert acc.total_mm == pytest.approx(100.0)
    assert acc.missing_days == 1
    assert acc.missing_dates == [date(2022, 6, 14)]


def test_accumulate_with_no_data_reports_all_missing(tmp_path) -> None:
    acc = imerg.accumulate({"id": "x", "lat": 24.55, "lon": 91.55}, date(2022, 6, 16), 2, cache_dir=tmp_path)
    assert acc.total_mm is None and acc.missing_days == 2


def test_invalid_run_rejected() -> None:
    with pytest.raises(ValueError):
        imerg.cache_path(date(2022, 6, 16), "early")
