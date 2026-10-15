"""Print the GIBS WMTS (EPSG:3857, best) capabilities for the layers used by the map (Phase 10, task 10.4).

Run manually: `.venv/Scripts/python scripts/inspect_gibs.py [layer_id ...]`
Output (format, tile matrix set, max zoom, time range, tile URL template) is copied into
`frontend/src/config/layers.js` and `docs/data_sources.md`.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET

import httpx

CAPS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/wmts.cgi?SERVICE=WMTS&REQUEST=GetCapabilities"
NS = {
    "w": "http://www.opengis.net/wmts/1.0",
    "ows": "http://www.opengis.net/ows/1.1",
}
DEFAULTS = ["IMERG_Precipitation_Rate", "MODIS_Terra_NDVI_8Day"]


def main() -> int:
    wanted = sys.argv[1:] or DEFAULTS
    text = httpx.get(CAPS, timeout=120.0, follow_redirects=True).text
    root = ET.fromstring(text)
    all_ids = [e.text for e in root.findall(".//w:Layer/ows:Identifier", NS)]
    print(f"layers in capabilities: {len(all_ids)}")
    # Show related ids too, so a wrong guess is visible.
    for hint in ("IMERG", "NDVI"):
        print(f"ids containing {hint}: {[i for i in all_ids if hint in i][:12]}")
    for layer in root.findall(".//w:Layer", NS):
        ident = layer.find("ows:Identifier", NS).text
        if ident not in wanted:
            continue
        print(f"\n== {ident}")
        print("title:", layer.find("ows:Title", NS).text)
        print("formats:", [f.text for f in layer.findall("w:Format", NS)])
        print("tile matrix sets:", [l.find("w:TileMatrixSet", NS).text for l in layer.findall("w:TileMatrixSetLink", NS)])
        dim = layer.find("w:Dimension", NS)
        if dim is not None:
            print("time default:", dim.find("w:Default", NS).text)
            values = [v.text for v in dim.findall("w:Value", NS)]
            print("time values (first/last 2):", values[:2], values[-2:])
        for r in layer.findall("w:ResourceURL", NS):
            print("tile template:", r.get("template"))
    for tms in root.findall(".//w:TileMatrixSet", NS):
        id_el = tms.find("ows:Identifier", NS)
        if id_el is None:  # the <TileMatrixSet> inside a layer's <TileMatrixSetLink>
            continue
        ident = id_el.text
        if ident in ("2km", "250m", "1km", "500m", "GoogleMapsCompatible_Level6", "GoogleMapsCompatible_Level9"):
            print(f"\nTileMatrixSet {ident}: {len(tms.findall('w:TileMatrix', NS))} levels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
