"""GPM IMERG V07 daily client: search, download, clip to Bangladesh, cache, district means.

Structure observed in a real `GPM_3IMERGDL` V07 granule (see `docs/data_sources.md`):
variable `precipitation` (mm/day, `_FillValue` -9999.9) with dimensions ordered
`(time, lon, lat)`, `time=1`, 0.1 degree global grid (3600 x 1800). The raw file is therefore
transposed to `(lat, lon)` before clipping.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import xarray as xr

from ...config import CACHE_DIR, STATIC_DIR, get_settings
from . import earthdata_auth

IMERG_CACHE_DIR = CACHE_DIR / "imerg"
VERSION = "07"
SHORT_NAMES = {"late": "GPM_3IMERGDL", "final": "GPM_3IMERGDF"}
VARIABLE = "precipitation"
BOX_HALF_WIDTH = 0.25  # degrees, centroid plus or minus
_EPS = 1e-6

BBox = tuple[float, float, float, float]  # west, south, east, north


class ImergError(RuntimeError):
    """Raised when an IMERG granule cannot be found, downloaded or understood."""


def cache_path(day: date, run: str, cache_dir: Path = IMERG_CACHE_DIR) -> Path:
    """Path of the clipped daily file, `{run}_{YYYYMMDD}.nc`."""
    _check_run(run)
    return cache_dir / f"{run}_{day:%Y%m%d}.nc"


def _check_run(run: str) -> None:
    if run not in SHORT_NAMES:
        raise ValueError(f"run must be one of {sorted(SHORT_NAMES)}, got {run!r}")


def _dim_name(da: xr.DataArray, candidates: tuple[str, ...]) -> str:
    for name in candidates:
        if name in da.dims:
            return name
    raise ImergError(f"none of {candidates} in dimensions {da.dims}")


def clip_to_bbox(source: xr.Dataset | xr.DataArray, bbox: BBox) -> xr.DataArray:
    """Return `precipitation` as a (lat, lon) array clipped to `bbox`, fill values as NaN.

    Handles the real granule layout `(time, lon, lat)` by dropping the length-1 time
    dimension and transposing. Coordinates are sorted ascending.
    """
    da = source[VARIABLE] if isinstance(source, xr.Dataset) else source
    if "time" in da.dims:
        if da.sizes["time"] != 1:
            raise ImergError(f"expected a single time step, got {da.sizes['time']}")
        da = da.isel(time=0, drop=True)
    lat_name = _dim_name(da, ("lat", "latitude"))
    lon_name = _dim_name(da, ("lon", "longitude"))
    da = da.transpose(lat_name, lon_name).rename({lat_name: "lat", lon_name: "lon"})
    da = da.sortby("lat").sortby("lon")
    west, south, east, north = bbox
    da = da.sel(lat=slice(south - _EPS, north + _EPS), lon=slice(west - _EPS, east + _EPS))
    if da.sizes["lat"] == 0 or da.sizes["lon"] == 0:
        raise ImergError(f"bounding box {bbox} does not intersect the granule grid")
    da = da.where(da >= 0)  # belt and braces: any unmasked negative fill value becomes NaN
    return da.astype("float32").rename(VARIABLE)


def _write_clipped(da: xr.DataArray, day: date, path: Path) -> None:
    da = da.assign_attrs(units="mm/day", long_name="IMERG daily precipitation, clipped")
    ds = da.to_dataset().expand_dims(time=[np.datetime64(day, "ns")])
    ds = ds.transpose("time", "lat", "lon")
    ds.attrs["source"] = "NASA GPM IMERG V07 (clipped to Bangladesh bounding box)"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".nc.part")
    ds.to_netcdf(tmp, encoding={VARIABLE: {"zlib": True, "complevel": 4, "_FillValue": np.float32(-9999.9)}})
    tmp.replace(path)


def fetch_day(
    day: date,
    run: str = "late",
    *,
    cache_dir: Path = IMERG_CACHE_DIR,
    bbox: BBox | None = None,
) -> Path:
    """Ensure the clipped IMERG file for `day` is cached and return its path.

    Downloads the global daily granule into a temporary directory, clips it, writes
    `{cache_dir}/{run}_{YYYYMMDD}.nc` and deletes the raw granule (even on failure).
    """
    _check_run(run)
    path = cache_path(day, run, cache_dir)
    if path.exists():
        return path
    bbox = bbox or get_settings().bbox

    import earthaccess

    earthdata_auth.login()
    results = earthaccess.search_data(
        short_name=SHORT_NAMES[run],
        version=VERSION,
        temporal=(f"{day}T00:00:00Z", f"{day}T23:59:59Z"),
        bounding_box=bbox,
    )
    if not results:
        raise ImergError(f"no {SHORT_NAMES[run]} v{VERSION} granule for {day}")
    with tempfile.TemporaryDirectory(prefix="imerg_raw_") as tmp:
        files = earthaccess.download(results[:1], tmp)
        if not files:
            raise ImergError(f"download of {SHORT_NAMES[run]} {day} returned no files")
        with xr.open_dataset(files[0]) as ds:
            if VARIABLE not in ds.data_vars:
                raise ImergError(f"variable {VARIABLE!r} not in granule; found {list(ds.data_vars)}")
            granule_day = np.datetime_as_string(ds["time"].values[0], unit="D")
            if granule_day != str(day):
                raise ImergError(f"granule time {granule_day} does not match requested {day}")
            clipped = clip_to_bbox(ds, bbox).load()
    _write_clipped(clipped, day, path)
    return path


def box_mean(da: xr.DataArray, lat: float, lon: float, half_width: float = BOX_HALF_WIDTH) -> float | None:
    """Mean of non-null cells inside centroid plus or minus `half_width`; None if no valid cell."""
    lat_ok = (da["lat"] >= lat - half_width - _EPS) & (da["lat"] <= lat + half_width + _EPS)
    lon_ok = (da["lon"] >= lon - half_width - _EPS) & (da["lon"] <= lon + half_width + _EPS)
    values = da.where(lat_ok & lon_ok, drop=True).values
    values = values[~np.isnan(values)]
    if values.size == 0:
        return None
    return float(values.mean())


def load_districts() -> list[dict[str, Any]]:
    """Districts from `data/static/districts.json`."""
    return json.loads((STATIC_DIR / "districts.json").read_text(encoding="utf-8"))


def _read_clipped(path: Path) -> xr.DataArray:
    with xr.open_dataset(path) as ds:
        da = ds[VARIABLE]
        if "time" in da.dims:
            da = da.isel(time=0, drop=True)
        return da.load()


def district_means(
    day: date,
    districts: Iterable[Mapping[str, Any]] | None = None,
    run: str = "late",
    *,
    cache_dir: Path = IMERG_CACHE_DIR,
) -> dict[str, float | None]:
    """Mean rainfall (mm/day) in each district box; None when every cell is fill/missing."""
    districts = list(districts) if districts is not None else load_districts()
    da = _read_clipped(fetch_day(day, run, cache_dir=cache_dir))
    return {d["id"]: box_mean(da, float(d["lat"]), float(d["lon"])) for d in districts}


@dataclass
class Accumulation:
    """Rainfall total over a window plus the days that could not be summed."""

    district: str
    end_date: date
    days: int
    total_mm: float | None
    missing_dates: list[date] = field(default_factory=list)

    @property
    def missing_days(self) -> int:
        """Number of days in the window with no usable cached value."""
        return len(self.missing_dates)


def accumulate(
    district: str | Mapping[str, Any],
    end_date: date,
    days: int,
    run: str = "late",
    *,
    cache_dir: Path = IMERG_CACHE_DIR,
) -> Accumulation:
    """Sum cached daily values for `days` days ending on `end_date` (inclusive).

    Uses only the cache (no network). Missing files or all-fill boxes count as missing days;
    `total_mm` sums the days that are available and is None if none are.
    """
    if days < 1:
        raise ValueError("days must be at least 1")
    _check_run(run)
    if isinstance(district, str):
        matches = [d for d in load_districts() if d["id"] == district]
        if not matches:
            raise KeyError(f"unknown district {district!r}")
        district = matches[0]
    lat, lon = float(district["lat"]), float(district["lon"])

    total, missing = 0.0, []
    seen = 0
    for offset in range(days):
        day = end_date - timedelta(days=offset)
        path = cache_path(day, run, cache_dir)
        value = box_mean(_read_clipped(path), lat, lon) if path.exists() else None
        if value is None:
            missing.append(day)
        else:
            total += value
            seen += 1
    return Accumulation(
        district=district["id"],
        end_date=end_date,
        days=days,
        total_mm=total if seen else None,
        missing_dates=sorted(missing),
    )


def main(argv: list[str] | None = None) -> int:
    """CLI: print the district-box mean rainfall (mm/day) for one date."""
    parser = argparse.ArgumentParser(description="IMERG district rainfall for one day")
    parser.add_argument("--date", required=True, type=date.fromisoformat)
    parser.add_argument("--run", choices=sorted(SHORT_NAMES), default="late")
    args = parser.parse_args(argv)
    districts = load_districts()
    means = district_means(args.date, districts, args.run)
    print(f"IMERG {args.run} {SHORT_NAMES[args.run]} v{VERSION}, {args.date}, mm/day")
    for d in districts:
        value = means[d["id"]]
        print(f"{d['id']:<12} {'null' if value is None else f'{value:8.2f}'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
