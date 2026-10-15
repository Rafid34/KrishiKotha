"""Probe real GIBS tile requests over Bangladesh for the layer/date combinations the map uses (Phase 10)."""
from __future__ import annotations

import math

import httpx

BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{layer}/default/{date}/{tms}/{z}/{y}/{x}.png"


def tile(lat: float, lon: float, z: int) -> tuple[int, int]:
    n = 2**z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return x, y


CASES = [
    ("IMERG_Precipitation_Rate", "GoogleMapsCompatible_Level6", 6, "2022-06-16"),
    ("IMERG_Precipitation_Rate", "GoogleMapsCompatible_Level6", 6, "1990-01-01"),
    ("MODIS_Terra_L3_NDVI_16Day", "GoogleMapsCompatible_Level9", 7, "2022-06-16"),
    ("MODIS_Terra_L3_NDVI_16Day", "GoogleMapsCompatible_Level9", 7, "2022-06-10"),
    ("MODIS_Terra_NDVI_8Day", "GoogleMapsCompatible_Level9", 7, "2026-10-10"),
    ("MODIS_Terra_NDVI_8Day", "GoogleMapsCompatible_Level9", 7, "2022-06-16"),
]


def main() -> int:
    with httpx.Client(timeout=60.0) as client:
        for layer, tms, z, day in CASES:
            x, y = tile(23.7, 90.4, z)
            url = BASE.format(layer=layer, date=day, tms=tms, z=z, y=y, x=x)
            r = client.get(url)
            print(f"{layer:<28} {day} z{z} -> HTTP {r.status_code} {r.headers.get('content-type')} {len(r.content)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
