"""Sanity check: confirm SMAP EASE-Grid 2.0 row/col nearest-neighbour math against the
already-cached granule from `inspect_smap.py` / `smap.py` (no new network calls if cached).
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from backend.app.services.nasa import smap  # noqa: E402

DAY = date(2026, 10, 10)


def main() -> int:
    raw_path = smap.fetch_granule(DAY)
    try:
        import h5py

        with h5py.File(raw_path, "r") as f:
            grid = f[smap.GROUP][smap.VARIABLE][...]
            lat_col = f["cell_lat"][:, 0]
            lon_row = f["cell_lon"][0, :]
            lat_full = f["cell_lat"][...]
            lon_full = f["cell_lon"][...]

        # Confirm the cylindrical-projection assumption: lat constant along rows, lon constant along columns.
        print("lat row-constancy max spread:", float(np.nanmax(np.ptp(lat_full, axis=1))))
        print("lon col-constancy max spread:", float(np.nanmax(np.ptp(lon_full, axis=0))))

        for d in smap.load_districts():
            row = smap._nearest_index(lat_col, float(d["lat"]))
            col = smap._nearest_index(lon_row, float(d["lon"]))
            print(
                f"{d['id']:<12} want=({d['lat']:.3f},{d['lon']:.3f}) "
                f"got=({lat_col[row]:.3f},{lon_row[col]:.3f}) value={grid[row, col]:.3f}"
            )

        # Distribution over the Bangladesh bounding box for context.
        bbox_lat = (lat_col >= 20.0) & (lat_col <= 27.0)
        bbox_lon = (lon_row >= 87.5) & (lon_row <= 93.0)
        sub = grid[np.ix_(bbox_lat, bbox_lon)]
        valid = sub[sub > smap.FILL_VALUE + 1.0]
        print(f"Bangladesh bbox: {valid.size} valid cells, min={valid.min():.2f} max={valid.max():.2f} mean={valid.mean():.2f}")
    finally:
        import shutil

        shutil.rmtree(raw_path.parent, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
