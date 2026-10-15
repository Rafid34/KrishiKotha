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

## Phase 10: SMAP, MODIS NDVI, GIBS (2026-10-15)

### SMAP L4 `SPL4SMGP` v008 (inspected before reading any values)

Command: `python scripts/inspect_smap.py 2026-10-10` (file `SMAP_L4_SM_gph_20261010T043000_Vv8011_001.h5`; one granule falls in the 04:30-07:30 UTC window around 06:00 UTC).

- Top level: `EASE2_global_projection`, `Geophysical_Data` (group), `Metadata` (group), `cell_column`, `cell_lat`, `cell_lon`, `cell_row`, `time`, `x`, `y`.
- `Geophysical_Data` holds 49 float32 `(y=1624, x=3856)` variables, including `sm_rootzone_pctl` (percent, 0 to 100, `_FillValue` -9999.0, "Root zone soil moisture (0-100 cm; percentile units)"), `sm_profile_pctl`, `sm_rootzone`, `sm_surface`, `sm_rootzone_wetness`, `precipitation_total_surface_flux`, `leaf_area_index`.
- The spec's `Geophysical_Data/sm_rootzone_pctl` is correct. Grid is `lambert_cylindrical_equal_area` (EASE-Grid 2.0, standard parallel 30). `cell_lat`/`cell_lon` are 2-D, but latitude is constant per row and longitude constant per column (`scripts/sanity_smap_grid.py`: spread 0.0), so the nearest cell comes from `cell_lat[:, 0]` and `cell_lon[0, :]`. Nearest cells were within 0.05 degrees of the centroids.
- Raw granule is downloaded to a temp dir and deleted; only a tiny JSON per day is cached.
- Validation: 2022-06-16 gives Sylhet 98.5, Sunamganj 96.5, Rangpur 96.5 percentile, in line with the POWER-derived 98th percentile for Sylhet (Phase 5). Dry-season day 2026-10-10: most districts 0 to 1.5.
- Fill values (-9999) at the nearest cell for Sunamganj, Khulna and Barishal (water or masked cells). Those districts use the POWER fallback; the UI says so.
- Live pipeline run 2026-10-10 to 2026-10-13: 20 SMAP values used; the other 12 district-days fell back to POWER; run status `ok`.

### MODIS NDVI through AppEEARS (`MOD13Q1.061`, `_250m_16_days_NDVI`)

- Login `POST /api/login` (Basic Auth) returns 200 with a token. `GET /api/product/MOD13Q1.061` lists `_250m_16_days_NDVI`. `VNP13A1.002` lists `500_m_16_days_NDVI` (note the underscore).
- Differences from what was assumed, found only by running the real API:
  1. Task latency: a 45-day, 8-point task took about 20 minutes (submitted 07:56 UTC, done 08:16 UTC). A 2003-2020 task finished within about 15 minutes. A pipeline run cannot wait, so it polls up to 20 s and reuses the pending task next run.
  2. `GET /api/status/{id}` returns HTTP 200 `status: pending` while queued, a body with only `progress` while processing (no `status` key), and HTTP 303 with `status: done` when finished. The client now handles all three.
  3. Result CSV NDVI is already scaled (0.4311), not an integer. Columns include `ID`, `Date`, `MOD13Q1_061__250m_16_days_NDVI`.
- Latest composites in the window: 2026-08-29 and 2026-09-14 (latency about one month). NDVI on 2026-09-14: Sylhet 0.390, Sunamganj 0.642, Khulna 0.530, Satkhira 0.646, Barishal 0.514, Rajshahi 0.608, Rangpur 0.788, Chattogram 0.387.
- Baseline: `python -m pipeline.build_ndvi_baseline` wrote `ndvi_mean` for all 8 districts (23 composite means each).
- Pipeline run 2026-10-10 to 2026-10-13: 32 of 32 district-days used the NDVI anomaly (for example Sylhet -0.041, Rajshahi +0.171). Earlier in the session, before the task finished, the same run used the documented Level 1 salinity formula (`degraded: false`) and `PipelineRun.detail.sources.MODIS.status` said `unavailable_fallback_no_ndvi` with the reason.
- Fallback rule for any later pending or failed task: salinity uses the Level 1 formula, `degraded: false` (Section 7.6, F2.2), and the district panel shows "NDVI anomaly unavailable".

### NASA GIBS (GetCapabilities, `python scripts/inspect_gibs.py`, 1330 layers)

| Layer id | Matrix set | Coverage start | Note |
|---|---|---|---|
| `IMERG_Precipitation_Rate` | `GoogleMapsCompatible_Level6` | 2000-06-01 | confirmed, PNG, daily, has gaps |
| `MODIS_Terra_NDVI_8Day` | `GoogleMapsCompatible_Level9` | 2025-02-12 | confirmed, but no imagery for the 2022 demo date |
| `MODIS_Terra_L3_NDVI_16Day` | `GoogleMapsCompatible_Level9` | 2000-03-05 | added; covers the demo date |

- Spec guessed tile matrix sets `2km` and `250m`; real ones are the `GoogleMapsCompatible_Level*` sets above.
- `scripts/probe_gibs_tiles.py`: dates inside a period snap to it (same bytes for 2022-06-10 and 2022-06-16); dates before coverage return HTTP 404, so the map shows a "no imagery for this date" message.
- Attribution "Imagery: NASA GIBS" is shown in the overlay control and the Leaflet attribution bar.
