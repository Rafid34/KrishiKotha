# Progress

| Phase | Status | Notes |
|---|---|---|
| 0: Environment setup | Done | Scaffold, deps, `npm run build` done. `check_env.py` exits 0; `verify_endpoints.py` passes (a) to (f) after Earthdata credentials were added. |
| 1: Static data, database, seed | Done | Verified: seed run twice gives 8 districts and 3 crops; `/api/health` returns ok. |
| 2: POWER client and baseline | Done | Verified: 13 tests pass; 8 baseline files written; Sylhet mid-June `rain30_mean` 623.2 mm > Rajshahi 188.1 mm. |
| 3: GPM IMERG client | Done | Verified: CLI prints 8 values for 2022-06-16 (Sylhet 164.8, Sunamganj 267.6 mm/day, Final Run); 21 tests pass; cached files about 22 KB each; raw granules deleted. |
| 4: Risk scoring engine | Done | Verified: 15 tests pass (76 assertions); all Section 7.6 formulas implemented exactly as written with named constants and level thresholds (<40 low, 40-69.99 moderate, >=70 high); degraded flag handles missing soil input. |

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

## Phase 4 details

- `services/risk/scoring.py`:
  - Implemented constants: `THRESHOLD_MODERATE` (40.0), `THRESHOLD_HIGH` (70.0), flood weights (`WEIGHT_FLOOD_RAIN3` = 0.40, `WEIGHT_FLOOD_RAIN7` = 0.35, `WEIGHT_FLOOD_SOIL` = 0.25), drought parameters (`WEIGHT_DROUGHT_SOIL` = 0.45, `WEIGHT_DROUGHT_RAIN` = 0.35, `WEIGHT_DROUGHT_HEAT` = 0.20, `DROUGHT_DEFICIT_SCALE` = 125.0, `DROUGHT_HEAT_MAX_ANOMALY` = 4.0), salinity parameters (`SALT_COAST_MAX_KM` = 150.0, `SALT_COAST_MIN_KM` = 20.0, `SALT_COAST_SPAN_KM` = 130.0, `SALT_SEASON_HIGH` = 100.0, `SALT_SEASON_MODERATE` = 60.0, `SALT_SEASON_LOW` = 20.0, `WEIGHT_SALT_SEASON_WITH_NDVI` = 0.40, `WEIGHT_SALT_DRY_WITH_NDVI` = 0.30, `WEIGHT_SALT_VEG_WITH_NDVI` = 0.30, `WEIGHT_SALT_SEASON_WITHOUT_NDVI` = 0.55, `WEIGHT_SALT_DRY_WITHOUT_NDVI` = 0.45, `SALT_NDVI_SCALE` = 0.10), and `SCORING_CONSTANTS` dictionary for echoing by `/api/sources`.
  - Functions: `level_for`, `clamp`, `score_flood`, `score_drought`, `score_salt`. Each scoring function returns `{"score": float, "level": str, "inputs": list[dict], "degraded": bool}` with scores clamped to 0 to 100 and rounded to 2 decimals.
  - Flood supports the Level 3 upstream rainfall percentile extension (`rain7_upstream_pctl`).
  - Salinity implements both the Level 1 formula without NDVI and Level 2 formula with NDVI.
- Tests: `backend/tests/test_scoring.py` with 15 test functions and 76 assertions (minimum required: 12 assertions), covering:
  - Level thresholds at 0, 39.99, 40.0, 55.0, 69.99, 70.0, 100.0.
  - Clamping utility.
  - Weights summation and constants verification.
  - Extreme rain giving flood score >= 80 (score 87.0, high level).
  - Flood with raw sample arrays and Level 3 upstream rainfall extension.
  - Flood missing soil input setting `degraded: True` and reweighting rain inputs.
  - Dry soil and rain deficit giving drought score >= 70 (score 75.5, high level).
  - Drought heat anomaly clamping and excess rainfall handling.
  - Drought missing soil input setting `degraded: True` and reweighting rain/heat inputs.
  - Inland district (coastal distance 350 km and 150 km) giving salt score 0.0.
  - Coastal district in April with 70% rain deficit giving salt score >= 70 (score 94.38, high level).
  - Salinity seasonality across months and date inputs.
  - Salinity with NDVI (Level 2).
  - Score determinism across repeated executions.
- Concerns recorded (per instructions, formulas were implemented without modification):
  - In Section 7.6 line 666, the salinity formula without NDVI is noted as `# degraded = false; documented Level 1 formula`. In contrast, Section 4 F2.2 line 163 notes: `If the task is pending or fails, scores fall back to the formula without NDVI and degraded: true`. In `scoring.py`, `degraded: False` is the default in Level 1 mode, but `degraded` can be explicitly overridden if a caller in Level 2 had a failed NDVI fetch.
  - Section 7.6 does not write out the exact algebraic formula when `soil_pctl` is missing for flood or drought, though Section 9 task 4.4 requires `missing soil input sets degraded: true`. As recorded in `docs/methodology.md`, remaining weights are normalized proportionally to sum to 1.0 (flood rain3: 0.40/0.75, rain7: 0.35/0.75; drought rain: 0.35/0.55, heat: 0.20/0.55).

