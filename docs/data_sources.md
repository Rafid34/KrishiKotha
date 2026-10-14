# Data Sources

## Phase 0 endpoint verification (2026-10-14)

Run with `python scripts/verify_endpoints.py`.

| Check | Result | Observation |
|---|---|---|
| (a) POWER daily point, Sylhet | Pass | Keys returned: `PRECTOTCORR`, `T2M`, `RH2M`, `ALLSKY_SFC_SW_DWN`. |
| (b) CMR `GPM_3IMERGDL` v07 | Pass | 1 granule for 2026-10-04. |
| (c) earthaccess environment login | Pass | Initially failed (`LoginStrategyUnavailable`, credentials empty); passes after credentials were added to `.env`. |
| (d) Open IMERG daily granule | Pass | Initially failed as a consequence of (c). Re-run: file `3B-DAY-L.MS.MRG.3IMERG.20261004-S000000-E235959.V07C.nc4`; variables `precipitation`, `precipitation_cnt`, `precipitation_cnt_cond`, `MWprecipitation`, `MWprecipitation_cnt`, `MWprecipitation_cnt_cond`, `randomError`, `randomError_cnt`, `probabilityLiquidPrecipitation`, `time_bnds`; dimensions `time=1, lon=3600, lat=1800, nv=2`. |
| (e) GIBS GetCapabilities | Pass | `IMERG_Precipitation_Rate` and `MODIS_Terra_NDVI_8Day` both present. |
| (f) CMR `SPL4SMGP` v008 | Pass | Latest granule 2026-10-11T21:00:00Z. |

### Earlier failures (c) and (d)

`EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD` in `.env` were empty. This was a missing prerequisite, not an endpoint deviation, and is resolved.

### Notes

- `earthaccess` 0.17.0 also accepts `EARTHDATA_TOKEN` as an alternative to username and password.
- `earthaccess` emits a `FutureWarning` about `DataGranule.size()` becoming an attribute. This is harmless.
- Python 3.11 is used through the `py -3.11` launcher. The `python3.11` shim on PATH is a broken uv trampoline.

## Phase 2: POWER daily point (2026-10-14)

- Request `parameters=PRECTOTCORR,T2M_MAX,RH2M,GWETROOT&community=AG&format=JSON` for Sylhet, 2022-06-10 to 2022-06-16: all four keys returned under `properties.parameter`, keyed by `YYYYMMDD`. Header reports `fill_value: -999.0`, API v2.10.0, `time_standard: LST`.
- Full 2001-01-01 to 2020-12-31 request returned 7305 days for all eight districts in a single call each.
- Note: the Phase 0 check (a) uses `T2M` and `ALLSKY_SFC_SW_DWN`, not the Phase 2 parameter set; both work.

## Phase 3: GPM IMERG daily V07 (2026-10-14)

Granule structure observed before writing the parser (Late Run `3B-DAY-L.MS.MRG.3IMERG.20261004-S000000-E235959.V07C.nc4`, and again for the Final Run `3B-DAY.MS.MRG.3IMERG.20220616-S000000-E235959.V07B.nc4`; both identical in layout):

- Variables: `precipitation`, `precipitation_cnt`, `precipitation_cnt_cond`, `MWprecipitation`, `MWprecipitation_cnt`, `MWprecipitation_cnt_cond`, `randomError`, `randomError_cnt`, `probabilityLiquidPrecipitation`, `time_bnds`.
- Dimensions: `time=1, lon=3600, lat=1800, nv=2`.
- **Difference from the spec's assumption:** `precipitation` is stored as `(time, lon, lat)`, not `(lat, lon)`. The parser drops `time` and transposes to `(lat, lon)` by dimension name. Coordinates are ascending (`lat` -89.95 to 89.95, `lon` -179.95 to 179.95, cell centres on x.x5).
- `precipitation` units are `mm/day` (a daily mean rate, so no x24 conversion); `_FillValue` is -9999.9 (xarray masks it to NaN on open).
- The `GPM_3IMERGDF` collection reports 1 granule per day; the Final granule for 2022-06-16 has the same variable list. CMR newest granule start: `GPM_3IMERGDL` 2026-10-12, `GPM_3IMERGDF` 2025-09-30 (Final Run lags by about a year in CMR, not 3.5 months, so Final is only usable for historical events).
- Clipping to the Bangladesh box (88.0, 20.5, 92.7, 26.7) gives a 62 x 47 grid; each cached file is about 22 KB (limit 5 MB).

### District values for 2022-06-16 (mm/day, mean of 0.1 degree cells within centroid +/- 0.25 degrees)

Command: `python -m backend.app.services.nasa.imerg --date 2022-06-16 --run final`

| District | Final Run (V07B) | Late Run (V07, same date) |
|---|---|---|
| Sylhet | 164.77 | 186.05 |
| Sunamganj | 267.55 | 286.56 |
| Khulna | 9.42 | 12.27 |
| Satkhira | 8.21 | 8.86 |
| Barishal | 14.87 | 17.40 |
| Rajshahi | 4.51 | 6.56 |
| Rangpur | 76.99 | 85.82 |
| Chattogram | 72.28 | 82.89 |

Sanity check passed: Sylhet and Sunamganj are both far above 20 mm/day during the June 2022 floods. The Late Run is higher than the Final Run in every district (the Final Run is gauge-adjusted); use Final for event replay and backtest. Maximum clipped cell value in the Final file is 391.3 mm/day.

## Phase 5: end-to-end pipeline runs (2026-10-14)

- `python -m pipeline.run_pipeline --start 2022-05-15 --end 2022-06-30 --run final`: status `ok`, 376 risk rows (8 districts x 47 dates), 1128 observations, 76 IMERG Final Run days fetched (2022-04-16 to 2022-06-30, of which 29 are lookback), POWER last data date 2022-06-30, no skipped district-dates. The first attempt stopped after a transient Earthdata login `ConnectionError`; see `docs/methodology.md` for the retry change.
- `python -m pipeline.run_pipeline --run late` (defaults: end = newest `GPM_3IMERGDL` granule, start = end - 29): status `ok`, IMERG last data date 2026-10-13, POWER last data date 2026-10-11, so soil wetness was at most 2 days stale.
- POWER daily latency observed on 2026-10-14: 2 to 3 days. IMERG Late Run: data for the previous day was available.
- Sylhet on 2022-06-16 (Final Run, V07): flood 98.0 (high), drought 0.9, salinity 0.0. `rain3` 286.7 mm (99.2nd percentile of the baseline), `rain7` 391.4 mm (96.6th), soil wetness 1.0 (98th percentile). Sunamganj 99.4 and Rangpur 99.0 flood, Chattogram 79.5; Rajshahi, Khulna and Satkhira are low for flood.
- `scripts/verify_offline.py` serves the API with `DATA_MODE=snapshot`, an empty database and all non-loopback sockets blocked: 11 checks pass and the server made 0 outbound attempts.
