# Data Sources

## Phase 0 endpoint verification (2026-10-14)

Run with `python scripts/verify_endpoints.py`.

| Check | Result | Observation |
|---|---|---|
| (a) POWER daily point, Sylhet | Pass | Keys returned: `PRECTOTCORR`, `T2M`, `RH2M`, `ALLSKY_SFC_SW_DWN`. |
| (b) CMR `GPM_3IMERGDL` v07 | Pass | 1 granule for 2026-10-04. |
| (c) earthaccess environment login | **Fail** | `LoginStrategyUnavailable: Either the environment variables EARTHDATA_USERNAME and EARTHDATA_PASSWORD must both be set, or EARTHDATA_TOKEN must be set for the 'environment' login strategy.` |
| (d) Open IMERG daily granule | **Fail** | Consequence of (c): `'NoneType' object has no attribute 'get': You must call earthaccess.login() before you can download data`, then `RuntimeError: IMERG download returned no files`. |
| (e) GIBS GetCapabilities | Pass | `IMERG_Precipitation_Rate` and `MODIS_Terra_NDVI_8Day` both present. |
| (f) CMR `SPL4SMGP` v008 | Pass | Latest granule 2026-10-11T21:00:00Z. |

### Cause of failures (c) and (d)

`EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD` in `.env` are empty. They need a free Earthdata Login account, which the agent cannot create. This is a missing prerequisite, not an endpoint deviation. Re-run both checks after filling in `.env`.

### Notes

- `earthaccess` 0.17.0 also accepts `EARTHDATA_TOKEN` as an alternative to username and password.
- `earthaccess` emits a `FutureWarning` about `DataGranule.size()` becoming an attribute. This is harmless.
- Python 3.11 is used through the `py -3.11` launcher. The `python3.11` shim on PATH is a broken uv trampoline.

## Phase 2: POWER daily point (2026-10-14)

- Request `parameters=PRECTOTCORR,T2M_MAX,RH2M,GWETROOT&community=AG&format=JSON` for Sylhet, 2022-06-10 to 2022-06-16: all four keys returned under `properties.parameter`, keyed by `YYYYMMDD`. Header reports `fill_value: -999.0`, API v2.10.0, `time_standard: LST`.
- Full 2001-01-01 to 2020-12-31 request returned 7305 days for all eight districts in a single call each.
- Note: the Phase 0 check (a) uses `T2M` and `ALLSKY_SFC_SW_DWN`, not the Phase 2 parameter set; both work.
