"""Smoke test of every NASA endpoint used by Krishi Kotha (Phase 0, task 0.6)."""
from __future__ import annotations

import os
import sys
import traceback
from datetime import date, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_env import ROOT, load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

POWER = os.environ.get("POWER_API_BASE", "https://power.larc.nasa.gov/api")
CMR = os.environ.get("CMR_BASE", "https://cmr.earthdata.nasa.gov/search")
GIBS_CAPS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/wmts.cgi?SERVICE=WMTS&REQUEST=GetCapabilities"
SYLHET = (24.8949, 91.8687)
TIMEOUT = httpx.Timeout(60.0)

state: dict = {}


def check_a() -> None:
    """POWER daily point for Sylhet, 3 days."""
    end = date.today() - timedelta(days=10)
    start = end - timedelta(days=2)
    params = {
        "parameters": "PRECTOTCORR,T2M,RH2M,ALLSKY_SFC_SW_DWN",
        "community": "AG",
        "latitude": SYLHET[0],
        "longitude": SYLHET[1],
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    r = httpx.get(f"{POWER}/temporal/daily/point", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    keys = list(r.json()["properties"]["parameter"].keys())
    print(f"parameter keys: {keys}")


def check_b() -> None:
    """CMR granule count for GPM_3IMERGDL v07 on one day."""
    day = date.today() - timedelta(days=10)
    params = {
        "short_name": "GPM_3IMERGDL",
        "version": "07",
        "temporal": f"{day}T00:00:00Z,{day}T23:59:59Z",
        "page_size": 5,
    }
    r = httpx.get(f"{CMR}/granules.json", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    entries = r.json()["feed"]["entry"]
    state["imerg_day"] = day
    print(f"granule count for {day}: {len(entries)}")
    if not entries:
        raise RuntimeError("zero GPM_3IMERGDL v07 granules found")


def check_c() -> None:
    """earthaccess login using the environment strategy."""
    import earthaccess

    auth = earthaccess.login(strategy="environment")
    if not getattr(auth, "authenticated", False):
        raise RuntimeError("earthaccess.login(strategy='environment') not authenticated")
    state["auth"] = auth
    print("earthaccess login success")


def check_d() -> None:
    """Open one IMERG daily granule and print variables and dimensions."""
    import earthaccess
    import xarray as xr

    day = state.get("imerg_day", date.today() - timedelta(days=10))
    results = earthaccess.search_data(
        short_name="GPM_3IMERGDL", version="07", temporal=(str(day), str(day)), count=1
    )
    if not results:
        raise RuntimeError("no IMERG granule returned by earthaccess")
    files = earthaccess.download(results, str(ROOT / "data" / "cache" / "verify"))
    if not files:
        raise RuntimeError("IMERG download returned no files")
    ds = xr.open_dataset(files[0])
    print(f"file: {Path(str(files[0])).name}")
    print(f"variables: {list(ds.data_vars)}")
    print(f"dimensions: {dict(ds.sizes)}")
    ds.close()


def check_e() -> None:
    """GIBS GetCapabilities contains the needed layer ids."""
    r = httpx.get(GIBS_CAPS, timeout=httpx.Timeout(120.0), follow_redirects=True)
    r.raise_for_status()
    for layer in ("IMERG_Precipitation_Rate", "MODIS_Terra_NDVI_8Day"):
        present = f"<ows:Identifier>{layer}</ows:Identifier>" in r.text
        print(f"layer {layer}: {'present' if present else 'ABSENT'}")
        if not present:
            raise RuntimeError(f"layer {layer} not in GetCapabilities")


def check_f() -> None:
    """CMR latest SPL4SMGP v008 granule date."""
    params = {
        "short_name": "SPL4SMGP",
        "version": "008",
        "sort_key": "-start_date",
        "page_size": 1,
    }
    r = httpx.get(f"{CMR}/granules.json", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    entries = r.json()["feed"]["entry"]
    if not entries:
        raise RuntimeError("no SPL4SMGP v008 granules found")
    print(f"latest granule date: {entries[0].get('time_start')} ({entries[0].get('title')})")


CHECKS = [
    ("a", "POWER daily point (Sylhet, 3 days)", check_a),
    ("b", "CMR GPM_3IMERGDL v07 granule count", check_b),
    ("c", "earthaccess environment login", check_c),
    ("d", "Open IMERG daily granule", check_d),
    ("e", "GIBS GetCapabilities layer ids", check_e),
    ("f", "CMR SPL4SMGP v008 latest granule", check_f),
]


def main() -> int:
    """Run all checks, print results, return non-zero when any fails."""
    failures = []
    for tag, label, fn in CHECKS:
        print(f"\n[{tag}] {label}")
        try:
            fn()
            print(f"[{tag}] SUCCESS")
        except Exception as exc:  # noqa: BLE001
            failures.append(tag)
            print(f"[{tag}] FAIL: {type(exc).__name__}: {exc}")
            if os.environ.get("VERBOSE"):
                traceback.print_exc()
    print("\nSummary:", "all passed" if not failures else f"failed: {', '.join(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
