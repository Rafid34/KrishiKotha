"""One-off: download one real SPL4SMGP granule and print its HDF5 group/variable layout.

Run manually: `.venv/Scripts/python scripts/inspect_smap.py [YYYY-MM-DD]`
Not part of the application; used to confirm group/variable names for `smap.py` (Phase 10,
task 10.1) before writing the real reader. Output is recorded in `docs/data_sources.md`.
"""
from __future__ import annotations

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_env import ROOT, load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")


def walk(h5obj, prefix: str = "") -> None:
    import h5py

    for key in h5obj.keys():
        item = h5obj[key]
        path = f"{prefix}/{key}"
        if isinstance(item, h5py.Group):
            print(f"GROUP  {path}")
            walk(item, path)
        else:
            print(f"DSET   {path}  shape={item.shape}  dtype={item.dtype}")
            if "pctl" in key or key in ("cell_lat", "cell_lon", "cell_row", "cell_column"):
                for aname, aval in item.attrs.items():
                    print(f"         attr {aname} = {aval!r}")


def main() -> int:
    import earthaccess
    import h5py

    day_arg = sys.argv[1] if len(sys.argv) > 1 else None
    day = date.fromisoformat(day_arg) if day_arg else date.today() - timedelta(days=5)

    auth = earthaccess.login(strategy="environment")
    print(f"authenticated: {getattr(auth, 'authenticated', False)}")

    results = earthaccess.search_data(
        short_name="SPL4SMGP",
        version="008",
        temporal=(f"{day}T05:00:00Z", f"{day}T07:00:00Z"),
        count=1,
    )
    print(f"granules found near 06:00 UTC on {day}: {len(results)}")
    if not results:
        print("retrying with a wider window (00:00-23:59 UTC)")
        results = earthaccess.search_data(
            short_name="SPL4SMGP", version="008", temporal=(str(day), str(day)), count=1
        )
        print(f"granules found for the whole day: {len(results)}")
    if not results:
        print("NO GRANULES FOUND")
        return 1

    with tempfile.TemporaryDirectory(prefix="smap_inspect_") as tmp:
        files = earthaccess.download(results[:1], tmp)
        if not files:
            print("download returned no files")
            return 1
        path = files[0]
        print(f"file: {Path(path).name}")
        with h5py.File(path, "r") as f:
            print("--- top-level groups ---")
            for key in f.keys():
                print(" ", key)
            print("--- full tree ---")
            walk(f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
