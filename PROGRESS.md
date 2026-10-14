# Progress

| Phase | Status | Notes |
|---|---|---|
| 0: Environment setup | Done | Scaffold, deps, `npm run build` done. `check_env.py` exits 0; `verify_endpoints.py` passes (a) to (f) after Earthdata credentials were added. |
| 1: Static data, database, seed | Done | Verified: seed run twice gives 8 districts and 3 crops; `/api/health` returns ok. |
| 2: POWER client and baseline | Done | Verified: 13 tests pass; 8 baseline files written; Sylhet mid-June `rain30_mean` 623.2 mm > Rajshahi 188.1 mm. |
| 3: GPM IMERG client | Done | Verified: CLI prints 8 values for 2022-06-16 (Sylhet 164.8, Sunamganj 267.6 mm/day, Final Run); 21 tests pass; cached files about 22 KB each; raw granules deleted. |

## Phase 0 details

Done:
- Folder tree from Section 6, git initialised, `.gitignore`.
- `requirements.txt`, `.venv` (Python 3.11.9), `requirements.lock`.
- `frontend/package.json`, `npm install`, `npm run build` succeeds on a minimal scaffold.
- `.env.example` (Section 11.10) and `.env` copied from it.
- `scripts/check_env.py` and `scripts/verify_endpoints.py`.

Verification (re-run 2026-10-14 after credentials were added): `python scripts/check_env.py` exits 0 and `python scripts/verify_endpoints.py` prints success for (a) to (f). See `docs/data_sources.md`.

Notes:
- `npm install` reports 8 vulnerabilities (2 critical). Not addressed.
- Use `py -3.11` on this machine, since the `python3.11` shim is broken.

## Phase 1 details

- `data/static/districts.json`, `crops.json`, `advice_templates.json` written from Sections 7.5 and 7.4 (exact values and Bangla text).
- `crops.json` stores stages with `start_month`/`end_month` (wrap-around allowed, e.g. Dec to Jan) plus an `off_season` block of 0.7.
- `backend/app`: `config.py`, `db.py`, `models.py` (all Section 7.1 entities), `seed.py` (idempotent upsert), `main.py`, `routers/meta.py` (`/api/health`).
- Run from the repo root: `.venv/Scripts/python -m backend.app.seed`.

## Phase 2 details

- `services/nasa/power.py`: `fetch_power()` returns a date-indexed DataFrame; -999 becomes NaN; file cache in `data/cache/power/`; retry with exponential backoff on network errors and HTTP 429/5xx.
- `services/risk/indicators.py`: `percentile_rank`, `rolling_sum`.
- `services/risk/baseline.py` and `pipeline/build_baseline.py`: write `data/baseline/{district}.json` and 2928 `baselines` rows (8 x 366).
- Tests: `backend/tests/test_power_client.py`, `test_indicators.py` with fixture `fixtures/power_sylhet_sample.json` (saved live response). `pytest.ini` sets `pythonpath = .`.
- Check script: `python scripts/check_baseline.py`.
- Decisions recorded in `docs/methodology.md`; POWER observations in `docs/data_sources.md`.

## Phase 3 details

- `services/nasa/earthdata_auth.py` (`login()`, `EarthdataAuthError`), `cmr.py` (`latest_granule_date()`, `CmrError`), `imerg.py` (`fetch_day`, `clip_to_bbox`, `box_mean`, `district_means`, `accumulate`, CLI).
- `config.py` gained `cmr_base` and `bbox_*` settings (already in `.env.example`).
- Real granule layout differs from the spec: `precipitation` is `(time, lon, lat)`, so the parser transposes to `(lat, lon)`. Details and the 2022-06-16 values (Late and Final) are in `docs/data_sources.md`.
- Raw granules go to a temporary directory and are removed after clipping; the Phase 0 leftover `data/cache/verify/` granule was deleted.
- Tests: `backend/tests/test_imerg_client.py` (8, synthetic grid in the real dimension order, no network).
- CLI: `python -m backend.app.services.nasa.imerg --date 2022-06-16 --run final`.
- Note: the Final Run collection in CMR currently ends 2025-09-30, so recent dates need `--run late`.
