"""Level 2: SPL4SMGP granule read at district points (Section 2.2, task 10.1).

Real HDF5 layout confirmed 2026-10-15 with `scripts/inspect_smap.py` against a live
`SMAP_L4_SM_gph_20261010T043000_Vv8011_001.h5` granule (see `docs/data_sources.md`):

- Group `Geophysical_Data` holds `sm_rootzone_pctl` (float32, percent, `_FillValue` -9999.0)
  on a (y=1624, x=3856) grid, matching the spec's assumed group/variable name exactly.
- `cell_lat` and `cell_lon` are top-level 2-D (y, x) datasets giving the geodetic centre of
  every cell on the global cylindrical EASE-Grid 2.0 (`EASE2_global_projection`,
  `lambert_cylindrical_equal_area`, standard parallel 30 degrees). Because this projection is
  a true cylinder, latitude varies only by row and longitude only by column, so the nearest
  cell can be found from the 1-D vectors `cell_lat[:, 0]` and `cell_lon[0, :]` without a full
  2-D nearest-neighbour search.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from ...config import CACHE_DIR, STATIC_DIR
from . import earthdata_auth
from .offline import ensure_online

SMAP_CACHE_DIR = CACHE_DIR / "smap"
SHORT_NAME = "SPL4SMGP"
VERSION = "008"
GROUP = "Geophysical_Data"
VARIABLE = "sm_rootzone_pctl"
FILL_VALUE = -9999.0
TARGET_HOUR_UTC = 6  # near local midday in Bangladesh (UTC+6); 3-hourly granules


class SmapError(RuntimeError):
    """Raised when a SPL4SMGP granule cannot be found, downloaded or understood."""


def cache_path(day: date, cache_dir: Path = SMAP_CACHE_DIR) -> Path:
    """Path of the tiny per-day district-value cache, `{YYYYMMDD}.json`."""
    return cache_dir / f"{day:%Y%m%d}.json"


def load_districts() -> list[dict[str, Any]]:
    """Districts from `data/static/districts.json`."""
    return json.loads((STATIC_DIR / "districts.json").read_text(encoding="utf-8"))


def _nearest_index(vector: np.ndarray, value: float) -> int:
    return int(np.argmin(np.abs(vector - value)))


def read_district_values(h5_path: Path, districts: Iterable[Mapping[str, Any]]) -> dict[str, float | None]:
    """`sm_rootzone_pctl` (0-100) at the nearest EASE-Grid 2.0 cell to each district centroid."""
    import h5py

    with h5py.File(h5_path, "r") as f:
        grid = f[GROUP][VARIABLE][...]
        lat_col = f["cell_lat"][:, 0]
        lon_row = f["cell_lon"][0, :]

    out: dict[str, float | None] = {}
    for d in districts:
        row = _nearest_index(lat_col, float(d["lat"]))
        col = _nearest_index(lon_row, float(d["lon"]))
        value = float(grid[row, col])
        out[d["id"]] = None if value <= FILL_VALUE + 1.0 else value
    return out


def fetch_granule(day: date, *, hour_utc: int = TARGET_HOUR_UTC) -> Path:
    """Download one SPL4SMGP granule for `day` near `hour_utc` UTC to a fresh temp directory.

    Caller is responsible for deleting `path.parent` once it is done reading the file.
    """
    ensure_online(f"SMAP download for {day}")
    import earthaccess

    earthdata_auth.login()
    centre = datetime(day.year, day.month, day.day, tzinfo=timezone.utc) + timedelta(hours=hour_utc)
    window = (centre - timedelta(hours=1, minutes=30), centre + timedelta(hours=1, minutes=30))
    results = earthaccess.search_data(
        short_name=SHORT_NAME, version=VERSION,
        temporal=(window[0].isoformat(), window[1].isoformat()), count=1,
    )
    if not results:
        # Fall back to any granule for the whole day if none sits near the target hour.
        results = earthaccess.search_data(
            short_name=SHORT_NAME, version=VERSION, temporal=(str(day), str(day)), count=1,
        )
    if not results:
        raise SmapError(f"no {SHORT_NAME} v{VERSION} granule for {day}")

    tmp_dir = Path(tempfile.mkdtemp(prefix="smap_raw_"))
    files = earthaccess.download(results[:1], str(tmp_dir))
    if not files:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise SmapError(f"download of {SHORT_NAME} {day} returned no files")
    return Path(files[0])


def district_values(
    day: date,
    districts: Iterable[Mapping[str, Any]] | None = None,
    *,
    cache_dir: Path = SMAP_CACHE_DIR,
) -> dict[str, float | None]:
    """Root-zone soil moisture percentile (0-100) per district for `day`, from SMAP L4.

    Downloads at most one granule per day (cached thereafter as a tiny JSON of district
    values), reads it with `h5py`, and deletes the raw granule immediately. Raises
    `SmapError` if no granule exists for the day; callers should catch this and fall back
    to POWER `GWETROOT` (Section 7.6, F2.1).
    """
    districts = list(districts) if districts is not None else load_districts()
    path = cache_path(day, cache_dir)
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        return {d["id"]: cached.get(d["id"]) for d in districts}

    raw_path = fetch_granule(day)
    try:
        values = read_district_values(raw_path, districts)
    finally:
        shutil.rmtree(raw_path.parent, ignore_errors=True)

    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.part")
    tmp.write_text(json.dumps(values), encoding="utf-8")
    tmp.replace(path)
    return values


def main(argv: list[str] | None = None) -> int:
    """CLI: print the district root-zone soil moisture percentile for one date."""
    parser = argparse.ArgumentParser(description="SMAP L4 district root-zone soil moisture percentile")
    parser.add_argument("--date", required=True, type=date.fromisoformat)
    args = parser.parse_args(argv)
    districts = load_districts()
    try:
        values = district_values(args.date, districts)
    except SmapError as exc:
        print(f"SMAP unavailable for {args.date}: {exc}")
        return 1
    print(f"SMAP {SHORT_NAME} v{VERSION}, {args.date}, {GROUP}/{VARIABLE}")
    for d in districts:
        v = values[d["id"]]
        print(f"{d['id']:<12} {'null' if v is None else f'{v:6.2f}'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
