# Progress

| Phase | Status | Notes |
|---|---|---|
| 0: Environment setup | Partial | Scaffold, deps, `npm run build` done. Endpoints (a), (b), (e), (f) pass. (c) and (d) blocked on Earthdata credentials. |
| 1: Static data, database, seed | Done | Verified: seed run twice gives 8 districts and 3 crops; `/api/health` returns ok. |
| 2: POWER client and baseline | Done | Verified: 13 tests pass; 8 baseline files written; Sylhet mid-June `rain30_mean` 623.2 mm > Rajshahi 188.1 mm. |

## Phase 0 details

Done:
- Folder tree from Section 6, git initialised, `.gitignore`.
- `requirements.txt`, `.venv` (Python 3.11.9), `requirements.lock`.
- `frontend/package.json`, `npm install`, `npm run build` succeeds on a minimal scaffold.
- `.env.example` (Section 11.10) and `.env` copied from it.
- `scripts/check_env.py` and `scripts/verify_endpoints.py`.

Outstanding (Phase 0 verification still fails; Phases 1 and 2 were run at the user's explicit request and do not need Earthdata credentials, but Phase 3 does):
- Fill `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD` in `.env`.
- Re-run `python scripts/check_env.py` (currently exits 1) and `python scripts/verify_endpoints.py` (c and d currently fail). See `docs/data_sources.md`.

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
