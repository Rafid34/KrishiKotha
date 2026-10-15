# Progress

| Phase | Status | Notes |
|---|---|---|
| 0: Environment setup | Done | Scaffold, deps, `npm run build` done. `check_env.py` exits 0; `verify_endpoints.py` passes (a) to (f) after Earthdata credentials were added. |
| 1: Static data, database, seed | Done | Verified: seed run twice gives 8 districts and 3 crops; `/api/health` returns ok. |
| 2: POWER client and baseline | Done | Verified: 13 tests pass; 8 baseline files written; Sylhet mid-June `rain30_mean` 623.2 mm > Rajshahi 188.1 mm. |
| 3: GPM IMERG client | Done | Verified: CLI prints 8 values for 2022-06-16 (Sylhet 164.8, Sunamganj 267.6 mm/day, Final Run); 21 tests pass; cached files about 22 KB each; raw granules deleted. |
| 4: Risk scoring engine | Done | Verified: 15 tests pass (76 assertions); all Section 7.6 formulas implemented exactly as written with named constants and level thresholds (<40 low, 40-69.99 moderate, >=70 high); degraded flag handles missing soil input. |
| 5: Pipeline runner, snapshots, read API | Done | Verified: Final Run 2022-05-15 to 2022-06-30 status ok (376 rows); `/api/risk?date=2022-06-16` returns 8 districts; 58 tests pass (14 in `test_api.py`); snapshot mode with network blocked serves `/api/risk` and made 0 outbound attempts. Patch applied afterwards (see Phase 5 patch): 61 tests pass. Spec Section 7.2 `date` param on `GET /api/risk/{district_id}` implemented: 62 tests pass. |
| 6: Advice engine, parser, SMS simulator API | Done | Verified: 140 tests pass (33 in `test_advice.py`, 38 in `test_parser.py`, 16 in `test_api.py`); verbatim Bangla templates from Section 7.4; 134-character limit enforced with `MessageLengthExceededError`; `POST /api/sim/sms` returns Bangla replies (welcome + advice) and logs 2 messages; observed conditions only, no forecasts. |
| 7: Frontend scaffold and risk map dashboard | Done | Verified: 22 vitest tests pass; `npm run build` succeeds; map renders 8 district markers with OpenStreetMap tiles; date 2022-06-16 with flood hazard shows Sylhet High (score 98.01, red marker); RiskBadge and Legend follow Section 8.4 (icon shape + colour + text label); fonts self-hosted (@fontsource Inter & Noto Sans Bengali); 360 px mobile width verified with zero horizontal overflow. |
| 8: District detail and event replay | Done | Verified: 147 backend tests pass (7 in `test_backtest.py`); 25 vitest tests pass; `npm run build` succeeds; `GET /api/backtest/sylhet-2022` returns Section 7.2 shape; five replay step dates derived directly from data using task 8.4 rules with zero hard-coded dates and zero threshold tuning; measured lead time 14 days (>= 3-day target); `EventReplay` renders 5 step chips, interactive date slider with play/pause, Recharts timeline chart with milestone markers, and lead time summary box; `DistrictPanel` renders score cards, `TrendChart` (60-day rainfall bars, soil wetness line, 90th percentile baseline line), `FactorBars` (from `/explain`), and live crop advice. |
| 9: Farmer simulator UI | Done | Verified: 147 backend tests pass (18 in `test_api.py`); 32 vitest tests pass (7 in `simulator.test.jsx`); `npm run build` succeeds; `PhoneMockup` renders centered feature phone mockup (~320 px wide) with monochrome LCD screen, keypad, input box, Send button, Call button; Bangla text guaranteed >= 18 px in Noto Sans Bengali (`lang="bn"`); Quick-fill buttons for `SYLHET AMAN`, `KHULNA BORO`, `RAJSHAHI AMAN`, `HELP`, `STOP`; typing `SYLHET AMAN` on demo date 2022-06-16 returns welcome and flood advice messages; side panel renders Rule ID (`flood_high_early`), triggering hazard (`Flood` / High), and underlying scores (Drought 0.9, Flood 98.0, Salinity 0.0); `AdviceCard` renders Bangla (>=18px) and English text with audio button; invalid input returns help message; zero horizontal overflow at 360 px width. |
| 10: SMAP, MODIS NDVI, GIBS overlays | Done | Verified: 167 backend tests pass; 45 vitest tests pass; `npm run build` succeeds; real SPL4SMGP v008 file inspected first (`Geophysical_Data/sm_rootzone_pctl`, EASE-Grid 2.0); live run 2026-10-10 to 2026-10-13 shows `soil_source: SMAP_L4` for 5 districts and the POWER fallback (shown in UI) for 3 water-cell districts; MOD13Q1.061 NDVI anomaly used for 32 of 32 district-days with product version in the panel; GIBS ids confirmed from GetCapabilities; overlay toggle with attribution and no-imagery fallback; `/api/sources` lists SMAP and MODIS. See Phase 10 details. |
| 11: Voice and Twilio gateway | Done | Verified: 187 backend tests pass (20 new in `test_voice_gateway.py`); 50 vitest tests pass (5 new in `audio.test.js`); `npm run build` succeeds; real gTTS call returned 72 KB `audio/mpeg` for the Sylhet advice; with `TWILIO_ENABLED=false` app startup imports neither `twilio` nor `gtts` (subprocess test); `POST /api/admin/broadcast` without `X-Admin-Key` returns 401, with the key and no `dry_run` it is a dry run (`sent: 0`, nothing logged or sent); Twilio webhooks tested with real signature validation (403 on bad signature) using a stubbed TTS. Manual checks not done: browser playback of the Call button, and a real Twilio SMS round trip (no verified number or tunnel available). See Phase 11 details. |

## Spec patch (2026-10-15)

Changes to `PROJECT_SPEC.md` only (no code, tests, or data files changed):
- **Section 7.2, `GET /api/risk/{district_id}`**: restored broken table row to a single line; added `date` query parameter (optional, default latest snapshot; the `days` window ends at this date) and complete example JSON.
- **Section 7.2, standalone paragraph**: added `coastal_factor` explain paragraph below the last API table row; removed the duplicate that had been glued onto the broken table row.
- **Section 7.6, Drought code block**: removed sentence about Tmax7 that was accidentally pasted onto the `d_soil` line; block is now identical to HEAD.
- **Section 7.6, missing-inputs paragraph**: added after the Drought closing fence; specifies that missing soil or expired soil drops the soil term and renormalizes remaining weights; missing Tmax7 drops the heat term and renormalizes remaining drought weights; both set `degraded` true and the relevant `inputs.*_missing` flag.
- **Section 7.7**: replaced the stale-days sentence with the 7-day max-age rule (`soil_stale_days` stored even when expired; older value counts as missing per Section 7.6).
- **F2.2**: changed fallback from `degraded: true` to the documented Level 1 formula (`degraded: false`), matching Section 7.6.

~~Open code follow-up: Section 7.6 and the new missing-inputs paragraph specify that a missing Tmax7 should drop the heat term and **renormalize** the remaining drought weights. The current `score_drought` in `scoring.py` instead zeroes `sub_heat` and keeps the full 0.20 weight, biasing the score low. A code change to `score_drought` (and its tests) is needed to match the spec.~~ → **Resolved** in the Section 7.6 missing-inputs implementation below.

## Section 7.6 missing-inputs implementation (2026-10-15)

Implemented the full missing-inputs paragraph from Section 7.6 for Tmax7 and soil wetness.

### Changes

**`backend/app/services/risk/scoring.py`**
- `score_drought`: restructured the heat-anomaly branch to track a `heat_missing` flag when none of `d_heat`, `tmax7+tbase`, or `t_anomaly` is provided. The scoring section now covers all four combinations of soil × heat availability:
  1. Both available: full formula (unchanged).
  2. Soil missing, heat available: existing reweighting over rain + heat (unchanged).
  3. Heat missing, soil available (**new**): drop heat term, renormalize soil and rain. `w_soil = 0.45/0.80 = 0.5625`, `w_rain = 0.35/0.80 = 0.4375`.
  4. Both missing (**new**): rain term only, `weight = 1.0`.
- In all degraded cases `heat_anomaly` entry has `value: None, weight: 0.0`; active weights sum to 1.0.
- `score_drought` now returns two new top-level flags: `tmax_missing: bool` and `soil_missing: bool`.
- `score_flood` now returns one new top-level flag: `soil_missing: bool`.
- Redundant pipeline patch `if tmax_missing: drought = {**drought, "degraded": True}` removed from `score_district_day`; `score_drought` now sets `degraded` internally.

**`pipeline/run_pipeline.py`**
- `score_district_day`: added `soil_missing = power.soil is None` and surfaced it in the outer `inputs` dict as `inputs["soil_missing"]`, consistent with the existing `inputs["tmax_missing"]`.
- Updated docstring to describe the drop-and-renormalize behavior for both missing inputs.

### Tests (67 pass, was 62)

Added five new tests in `backend/tests/test_scoring.py`:
- `test_drought_missing_tmax_drops_heat_term_and_renormalizes`: verifies heat entry has `value: None, weight: 0.0`; verifies active weights sum to 1.0; checks exact renormalized score (soil_pctl=10, deficit=0.80 → 94.38).
- `test_drought_missing_tmax_score_exceeds_zero_heat_method`: confirms new score (94.38) > old biased score (75.5) for identical remaining inputs.
- `test_drought_missing_tmax_sets_degraded_and_flag`: `degraded=True`, `tmax_missing=True`; full-input call gives `degraded=False`, both flags False.
- `test_soil_missing_flag_for_flood_and_drought`: `soil_missing=True` on flood and drought when soil is absent; `soil_missing=False` when present.
- `test_drought_both_soil_and_tmax_missing`: only rain term used with `weight=1.0`; active weights still sum to 1.0.

Updated two existing pipeline tests in `backend/tests/test_pipeline.py`:
- `test_expired_soil_triggers_degraded_fallback`: added `assert expired.inputs["soil_missing"] is True`.
- `test_missing_soil_marks_degraded`: added `assert row.inputs["soil_missing"] is True`.

### Snapshot impact

Inspected `data/snapshots/sylhet_2022.json` (376 rows, 8 districts) and `data/snapshots/latest_30d.json` (240 rows). **No rows have `tmax_missing=True` or `soil_wetness=None`**: all rows were scored with complete inputs. Re-exporting would produce structurally different JSON (new `tmax_missing`/`soil_missing` keys in the flood and drought sub-dicts, and `soil_missing: false` in the outer inputs dict) but every stored `drought_score`, `flood_score`, and `salt_score` value would remain identical. No snapshot files were modified.

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


## Phase 5 details

- `pipeline/run_pipeline.py`: `--mode live|snapshot`, `--start`, `--end`, `--run late|final`. Live mode fetches IMERG (with a 29-day lookback), POWER `GWETROOT` and `T2M_MAX`, scores, upserts `risk_snapshots` and `observations`, and writes a `PipelineRun` with per-source status. Exit 0 only for status `ok`. Without `--start`/`--end` it scores the 30 days ending at the newest IMERG granule. `--mode snapshot` just loads `data/snapshots/*.json`.
- `pipeline/build_snapshot.py` writes `data/snapshots/latest_30d.json` (240 rows) and `sylhet_2022.json` (376 rows, all districts; see `docs/methodology.md`). Both are committed (about 1.7 MB).
- `backend/app/services/snapshots.py` (export, idempotent load), `services/nasa/offline.py` (`ensure_online()` guard used by POWER, CMR, Earthdata and IMERG clients), `errors.py` (uniform error body), `timeutil.py`, `schemas.py`.
- Routes per Section 7.2: `/api/districts`, `/api/crops` (`routers/districts.py`), `/api/risk`, `/api/risk/{id}`, `/api/risk/{id}/explain` (`routers/risk.py`), `/api/health`, `/api/sources`, `/api/pipeline/status` (`routers/meta.py`). `/api/layers`, advice, messaging, backtest and admin routes belong to later phases.
- `main.py` runs `create_all` and seed at startup, and loads snapshots when `DATA_MODE=snapshot`.
- Tests: `test_api.py` (14, in-memory DB), `test_pipeline.py` (8, fake fetchers, snapshot round trip, offline guard). `conftest.py` forces `DATA_MODE=live` for tests.
- Offline check: `python scripts/verify_offline.py` (real uvicorn, snapshot mode, empty DB, non-loopback sockets blocked and logged). This is a process-level block, not an OS firewall.

Deviations and open points:
- Also ran `--run late` for the 30 days to 2026-10-13 (Section 11.4), so `latest_30d.json` holds recent data rather than the 2022 event. This went beyond the single Final Run requested.
- `sylhet_2022.json` contains all 8 districts, so `/api/risk?date=2022-06-16` returns 8 districts in snapshot mode.
- `/api/sources` keeps the Section 7.2 list shape, so it does not yet echo `SCORING_CONSTANTS`; decide before Phase 12.
- The first Final Run attempt failed on a transient Earthdata login error (run row 1 is `failed` in the local DB, not exported). Retries were added.
- `npm install` vulnerabilities from Phase 0 are still not addressed.

## Phase 5 patch

Changes:
- POWER soil max age: `MAX_SOIL_AGE_DAYS = 7` in `pipeline/run_pipeline.py`. A latest soil value older than 7 days (8 or more) counts as missing: `power_indicators` returns `soil` and `soil_date` as None, so scoring takes the existing degraded fallback. `soil_stale_days` still records the age of the expired value. Not in Section 7.7, which only says to store stale days; this is an added rule.
- Salinity explain: `/api/risk/{id}/explain` now returns the `coastal_proximity` entry as `salt.coastal_factor` (`name`, `raw` km, `value` 0 to 100, `multiplier` = value/100, `source`, `data_date`, no weight) and removes it from `salt.inputs`. The remaining weights sum to 1.0 (0.55 + 0.45, or 0.40 + 0.30 + 0.30 with NDVI). `coastal_factor` is null for flood and drought. `score_salt`, stored snapshots and scores are unchanged; the split happens only when building the explain response. This adds a field not in the Section 7.2 example, and `salt.inputs` no longer lists the coastal entry that the Section 7.6 weights table implied.
- Tests: 61 pass (was 58). Added `test_power_soil_max_age_boundary`, `test_expired_soil_triggers_degraded_fallback` and `test_salt_explain_separates_coastal_factor`; the `test_api.py` salt fixture now has a realistic input list.

Not done (at time of patch):
- `date` query on `GET /api/risk/{district_id}`: skipped because Section 7.2 defined only `days` for this route. Subsequently added — see **Section 7.2 `date` param** follow-up below.

## Section 7.2 `date` param on `GET /api/risk/{district_id}`

Spec change (2026-10-15): Section 7.2 added an optional `date` query parameter to `GET /api/risk/{district_id}`. Default is the district's latest snapshot; the `days` window ends at that date.

Changes:
- `backend/app/routers/risk.py`: `risk_series` now accepts `date: date | None = Query(None, ...)`. When supplied, `last = date`; otherwise `last` is resolved from `max(RiskSnapshot.date)` as before. No other logic changed.
- `backend/tests/test_api.py`: added `test_risk_series_date_param` — requests a June 2022 window (fixture data) with `date=2022-06-15` and verifies the window ends there (2022-06-16 excluded), then checks `days=2` and `days=1` sub-windows.
- Tests: 62 pass (was 61).

Recorded, behavior unchanged:
- Missing soil reweighting: Section 7.6 does not give a formula when `soil_pctl` is missing. The engine renormalizes the remaining weights (flood 0.40/0.75 and 0.35/0.75; drought 0.35/0.55 and 0.20/0.55) and sets `degraded`. See `docs/methodology.md`. This now also fires for soil older than 7 days.
- Missing Tmax7: `power_indicators` gives `tmax7` None when no `T2M_MAX` exists in the 7-day window. `score_drought` then treats the heat sub-score as 0 but keeps its full 0.20 weight, so there is no reweighting and the score is biased low. The pipeline only sets drought `degraded` and `inputs.tmax_missing`. This differs from the soil case. If soil and Tmax7 are both missing, the 0 heat score still gets 0.20/0.55 of the weight.
- Salinity degraded flag contradiction: Section 7.6 says salinity without NDVI is `degraded = false` (documented Level 1 formula), while Section 4 F2.2 says a pending or failed NDVI task falls back to the formula without NDVI with `degraded: true`. Level 1 has no NDVI, so the code follows 7.6 (`degraded` false). Revisit when Phase 10 adds NDVI. The spec should name the winning rule.

## Phase 6 details

Implemented Phase 6: Advice engine, parser, and SMS simulator API (Sections 7.4, 7.5, 9).

### Implemented components
- **`backend/app/services/advice/stages.py`**:
  - `get_crop_stage`: maps `(crop_id, date)` to crop stage key and hazard sensitivities (`flood`, `drought`, `salt`).
  - Supports wrap-around stages (e.g. Boro Dec to Jan).
  - Implements overlapping stage rule from `docs/methodology.md`: later stage in `crops.json` order wins (e.g., Aman July resolves to `transplanting`).
  - Dates falling outside all stages map to `off_season` with 0.7 sensitivity across all hazards.
- **`backend/app/services/advice/rules.py`**:
  - `select_advice_rule`: evaluates hazards in order `(flood, drought, salt)`.
  - Effective score is `score * crop_stage_sensitivity`, capped at 100.
  - Highest effective score at or above 40 wins. Ties broken by evaluation order (`flood` > `drought` > `salt`).
  - If no hazard >= 40, returns `none_low` with level `low`.
  - Implements rule mapping:
    - Flood: `flood_high_harvest` for grain_filling_harvest stage; `flood_high_early` for other stages; `flood_moderate_any` for moderate.
    - Drought: `drought_high_transplant` for Aman rice in nursery or transplanting; `drought_moderate_any` for moderate or other high cases.
    - Salinity: `salt_high_any` for high or moderate salinity.
- **`backend/app/services/advice/composer.py`**:
  - `compose_advice`: loads templates from `data/static/advice_templates.json`.
  - Normalises Unicode text to NFC (`unicodedata.normalize("NFC", ...)`).
  - Enforces strict 134-character limit on Bangla text (`MAX_BANGLA_SMS_CHARS = 134`), raising `MessageLengthExceededError` if exceeded.
  - Verbatim templates from Section 7.4; messages describe observed conditions only with no forecast wording.
- **`backend/app/services/messaging/parser.py`**:
  - `parse_message`: parses English and Bangla district and crop names with whitespace and case tolerance.
  - Commands: `HELP` / `সাহায্য`, `STOP` / `বন্ধ`, `1` / `১`, `2` / `২` (feedback loop).
- **`backend/app/services/messaging/gateway.py` & `sim_gateway.py`**:
  - `MessagingGateway` abstract interface with `send_sms`.
  - `SimGateway`: in-memory simulator gateway recording sent messages without network calls.
- **`backend/app/services/messaging/handler.py`**:
  - `handle_inbound_sms`: parses inbound SMS, calculates salted SHA-256 phone hash, upserts `Subscriber`, generates replies, and logs messages.
  - Registration command (`<DISTRICT> <CROP>`): generates two replies (`welcome` and latest snapshot advice) and creates exactly two `MessageLog` records (`direction="out"`, `channel="sim"`).
  - Stop command (`STOP`): sets `subscriber.active = False`, logs and returns `stopped` message.
  - Help / unknown command: logs and returns `help` message.
- **`backend/app/schemas.py`**:
  - Added `AdviceRequest`, `AdviceOut`, `SimSmsRequest`, `SimReply`, `SimSmsOut`.
  - Resolved Python 3.11 type evaluation collision by importing `date as dt_date` to prevent field name shadowing.
- **`backend/app/routers/advice.py`**:
  - `POST /api/advice`: returns `AdviceOut` for given district, crop, and optional date. Validates district and crop exist (404 on unknown).
- **`backend/app/routers/messaging.py`**:
  - `POST /api/sim/sms`: accepts `{"from": "...", "body": "..."}`, calls `handle_inbound_sms`, returns replies and `subscriber_id`.
- **`backend/app/main.py`**:
  - Mounted `advice.router` and `messaging.router`.

### Tests (140 pass, was 67)
- **`backend/tests/test_advice.py`** (33 tests):
  - `test_verbatim_templates_from_spec`: asserts all 10 templates match Section 7.4 verbatim in Bangla and English.
  - `test_bangla_length_limit_all_templates`: verifies all templates are <= 134 characters.
  - `test_134_char_limit_enforced_by_composer`: verifies `MessageLengthExceededError` is raised when text exceeds 134 characters.
  - `test_messages_describe_observed_conditions_only_never_forecasts`: asserts absence of forecast terms (`next week`, `forecast`, `আগামী সপ্তাহ`, `পূর্বাভাস`).
  - `test_all_templates_render_for_8_districts_by_3_crops`: parametrized test for all 24 district × crop combinations checking no unresolved placeholders.
  - `test_rule_selection_order_and_priorities`: checks flood/drought/salt priority, tie-breaking, and `none_low` fallback.
  - `test_flood_rule_conditions`, `test_drought_rule_conditions`, `test_salt_rule_conditions`: verifies stage and level branches.
  - `test_crop_stages_mapping_overlap_and_offseason`: tests overlap resolution, wrap-around months, and off-season sensitivities.
- **`backend/tests/test_parser.py`** (38 tests):
  - 17 test cases for English and Bangla district and crop parsing with mixed case, extra spaces, and filler words.
  - 8 test cases for `HELP` and `STOP` commands in English and Bangla.
  - 4 test cases for feedback commands (`1`, `2`, `১`, `২`).
  - 9 test cases for invalid inputs, missing tokens, and empty strings.
- **`backend/tests/test_api.py`** (+4 tests):
  - `test_advice_endpoint`: verifies 200 OK on valid inputs, 404 on unknown district or crop.
  - `test_sim_sms_roundtrip`: verifies subscriber creation, two replies (welcome and advice), exactly two `message_logs` entries, `STOP` deactivation, and `HELP` response.

### Verification
- `pytest`: 140 passed in 5.4s.
- `POST /api/sim/sms` with `{"from": "+8801700000000", "body": "SYLHET AMAN"}` executed and verified live:
  - Status: 200 OK
  - Reply 1: `কৃষি কথায় স্বাগতম। আপনার এলাকা ও ফসল নথিভুক্ত হয়েছে। আমরা সতর্কবার্তা পাঠাব।`
  - Reply 2: `মাটির আর্দ্রতা কমছে। সম্ভব হলে ভোরে বা সন্ধ্যায় হালকা সেচ দিন।`
  - `subscriber_id`: 1

## Phase 7 details

Implemented Phase 7: Frontend scaffold and risk map dashboard (Sections 8, 9).

### Implemented components
- **Configuration & Setup**:
  - `frontend/vite.config.js`: configured `envDir: '..'`, proxy `/api` to `http://localhost:8000`, and Vitest configuration.
  - `frontend/src/styles/tokens.css`: design tokens from Section 8.4 (`--bg`, `--surface`, `--ink`, `--ink-muted`, `--brand`, `--brand-dark`, `--risk-low`, `--risk-moderate`, `--risk-high`, `--nasa-blue`, spacing scale, radius, typography).
  - `frontend/src/styles/global.css`: CSS reset, focus visible rings (`3px solid var(--brand)`), `prefers-reduced-motion` handling, card styles, and Leaflet z-index management.
- **Typography & Self-hosted Fonts**:
  - Self-hosted Inter (400, 500, 600, 700) and Noto Sans Bengali (400, 500, 700) via `@fontsource` packages imported in `main.jsx`.
  - Scoped `[lang="bn"]` font rule ensuring Bengali characters render with Noto Sans Bengali.
- **i18n Localization**:
  - `src/i18n/en.json` & `src/i18n/bn.json`: translation keys for navigation, dashboard titles, hazards, risk levels, and disclaimers.
  - `src/i18n/index.jsx`: `LangProvider`, `useLang` hook, and `t()` translator with English fallback, persisted in React memory state.
- **API Client**:
  - `src/api/client.js`: fetch wrapper normalizing backend responses and errors for districts, crops, risk snapshots, time series, explain factors, and SMS simulation.
- **UI Components & Accessibility (§8.4)**:
  - `src/components/Layout.jsx`: persistent shell with brand header, responsive navigation links (Dashboard, Replay, Simulator, Method), and language switcher (`বাংলা` / `EN`).
  - `src/components/RiskBadge.jsx` & `LevelIcon`: SVG icon shapes (circle for low, triangle for moderate, square for high) accompanied by text labels and colors, strictly adhering to Section 8.4 accessibility rule that risk levels must never rely on colour alone.
  - `src/components/Legend.jsx`: map legend rendering the three risk levels with their corresponding SVG shapes, colors, and localized text. Placed as a Leaflet custom control via React portal.
  - `src/components/HazardToggle.jsx`: native radio inputs in a styled pill container with keyboard navigation and visible focus rings.
  - `src/components/DataFreshness.jsx`: data freshness strip displaying latest observation dates for IMERG rainfall, POWER soil wetness, and T2M_MAX temperature.
  - `src/components/DistrictPanel.jsx`: district names (both languages), three score cards with `RiskBadge`, date, and mandatory "Based on NASA satellite data. Not an official government warning." disclaimer. Includes mobile media queries ensuring comfortable fit at <=360px.
  - `src/components/RiskMap.jsx`: Leaflet map with OpenStreetMap tiles, centered on Bangladesh, with 8 circle markers sized and coloured by the selected hazard level, aria-labels (`Sylhet, flood risk high, score 98`), interactive tooltips, and district selection handler.
  - `src/pages/Dashboard.jsx`: 65/35 desktop layout (>=1024px), stacked mobile layout (<1024px), default demo date `2022-06-16`, hazard toggle, date picker, map, and district detail panel.
- **Utilities & Unit Tests**:
  - `src/utils/risk.js` & `src/utils/format.js`: scoring thresholds, level metadata, hazard labels, score-to-level mapping, and locale-aware number/date formatting.
  - `src/__tests__/risk.test.js`: 22 Vitest tests covering LEVEL_META, levelColor, levelLabel, levelIcon, scoreToLevel thresholds (39.99/40/69.99/70), and hazardLabel.

### Verification
- `npm test`: 22 passed in 245ms.
- `npm run build`: built production bundle in 1.02s with zero errors or warnings.
- `GET /api/risk?date=2022-06-16` queried via Vite proxy: verified all 8 districts returned with Sylhet flood score 98.01 (High level, red marker).
- 360 px width check: verified mobile responsiveness down to 360px with `overflow-x: hidden` and zero horizontal overflow.
- `pytest`: 140 backend tests pass.

## Phase 8 details

Implemented Phase 8: District detail and event replay (Sections 7.2, 8.2, 8.4, 9).

### Implemented components

- **`backend/app/services/backtest.py`**:
  - `compute_backtest`: derives the five replay step dates, milestone dates, lead time, and reference onset citation directly from snapshot series data without hard-coded dates.
  - Derivation rules from task 8.4:
    - Step 1 ("Rain begins"): first day 3-day rainfall exceeds the 50th baseline percentile (`rain3_pctl > 50`) -> `2022-05-15`.
    - Step 2 ("Rain builds"): first day `f_rain7` is at least 60 (`rain7_pctl >= 60`) on or after Step 1 -> `2022-05-15`.
    - Step 3 ("Heavy rain"): first day flood level is Moderate (`flood_level == "moderate"`, score 40–69.99) on or after Step 2 -> `2022-05-25`.
    - Step 4 ("Extreme rain"): first day flood level is High (`flood_level == "high"`, score >= 70) on or after Step 3 -> `2022-06-02`.
    - Step 5 ("Flood"): reference flood onset date -> `2022-06-16`.
  - Milestone dates: `first_moderate = "2022-05-25"`, `first_high = "2022-06-02"`.
  - Measured lead time: 14 days (`(2022-06-16 - 2022-06-02).days = 14`).
  - Strict preservation of fixed thresholds: no thresholds tuned on the Sylhet 2022 event.
  - Reference onset citation: Flood Forecasting and Warning Centre (FFWC) BWDB *Annual Flood Report 2022* & UN OCHA / ReliefWeb *Bangladesh: Floods - Jun 2022*.
- **`backend/app/routers/backtest.py`**:
  - `GET /api/backtest/sylhet-2022`: queries Sylhet 2022 event snapshots (`2022-05-15` to `2022-06-30`), observations (`precip_mm`, `soil_wetness`), and baseline 90th percentile by day of year; returns `BacktestOut` per Section 7.2.
- **`backend/app/schemas.py`**:
  - Added `ReplayStep`, `BacktestPoint`, and `BacktestOut` response models.
- **`backend/app/main.py`**:
  - Mounted `backtest.router` at `/api/backtest`.
- **`backend/tests/test_backtest.py`** (7 tests):
  - `test_synthetic_series_known_dates`: asserts exact derivation of 5 step dates, milestone dates, and lead time on a known synthetic series.
  - `test_lead_time_calculation_variations`: verifies 3-day and 7-day lead times.
  - `test_flood_never_reaches_high`: verifies safe nulls when High level is never reached.
  - `test_empty_series_handled_safely`: graceful handling of empty series without exceptions.
  - `test_public_citation_present`: confirms citation is returned.
  - `test_api_backtest_sylhet_endpoint`: integration test asserting 200 OK and Section 7.2 shape on `GET /api/backtest/sylhet-2022`.
  - `test_api_backtest_empty_database`: asserts 404 on unseeded database.
- **`frontend/src/api/client.js`**:
  - Added `getBacktestSylhet()` wrapper.
- **`frontend/src/components/FactorBars.jsx`**:
  - Renders factor breakdown from `/explain` with localized titles, progress bars, weights, raw sensor measurements, source/date provenance, coastal proximity multiplier card (salinity), and degraded fallback badge.
- **`frontend/src/components/TrendChart.jsx`**:
  - Recharts composed chart showing 60-day rainfall bars (`rain_mm`, blue), soil wetness line (`soil_pct`, orange), baseline 90th percentile dashed reference line, custom tooltip, and accessible summary text below chart per Section 8.4.
- **`frontend/src/components/DistrictPanel.jsx`**:
  - Full implementation of Section 8.2: district names in both languages, 3 score cards with `RiskBadge` (clickable to switch factor view), embedded `TrendChart`, embedded `FactorBars`, "Advice for farmers" section with crop selector (Aman, Boro, Aus) calling live `/api/advice`, and mandatory disclaimer.
- **`frontend/src/pages/EventReplay.jsx`**:
  - Full implementation of Section 8.2:
    - 5 step chips with active highlight as timeline advances.
    - Interactive timeline player with range slider and Play/Pause animation.
    - Recharts timeline chart with rainfall bars, flood score line, threshold lines (Moderate 40, High 70), milestone vertical markers (`first_moderate`, `first_high`, reference onset `2022-06-16`), and current slider date marker.
    - Summary box with lead time banner ("Warning came 14 days before the flood" from API), fixed thresholds explanation, reference citation, and disclaimer.
- **`frontend/src/i18n/en.json` & `bn.json`**:
  - Added translation keys for FactorBars, TrendChart, EventReplay, and DistrictPanel.
- **`frontend/src/__tests__/replay.test.js`**:
  - Added 3 Vitest tests for backtest client and replay step sequencing.

### Verification

- `pytest`: 147 backend tests pass (7 in `test_backtest.py`).
- `npm test`: 25 frontend vitest tests pass across 2 test files.
- `npm run build`: builds production bundle cleanly with zero errors.
- `GET /api/backtest/sylhet-2022`: verified returning HTTP 200 with 47 points, `lead_time_days: 14`, and 5 derived step dates.
- Replay lead time equals API value: verified `EventReplay.jsx` displays `lead_time_days` from the API.
- District detail verified: clicking district shows scores, TrendChart, FactorBars, and farmer advice.

## Phase 9 details

Implemented Phase 9: Farmer simulator UI (Sections 7.2, 8.2, 8.4, 9).

### Implemented components

- **`frontend/src/components/PhoneMockup.jsx`** (Task 9.1):
  - Implements Section 8.2 feature phone layout: centered chassis (320 px wide) with dark matte casing, earpiece speaker slit, and brand label ("KRISHI 100").
  - Monochrome LCD screen styling (`#CAD7B0` background gradient, dark pixel ink `#142210`, inner shadow, status bar with signal bars, battery `[85%]`, carrier "KrishiNet", and footer).
  - Scrollable message viewport supporting user messages (`sender: 'farmer'`) and Krishi Kotha system replies (`sender: 'krishi'`).
  - **Strict typography compliance**: Bangla messages rendered with `lang="bn"`, `font-size: 18px !important`, and `font-family: var(--font-bangla) !important` in Noto Sans Bengali.
  - Physical feature phone keypad detailing: soft navigation keys (Call, End, 4-way D-Pad) and 12 alphanumeric keys (1–9, *, 0, #).
  - Under-phone controls: accessible input box (`placeholder="SYLHET AMAN"`), Send button (`var(--brand)`), and Call button (Level 2 voice).
  - Full keyboard accessibility and minimum 44 px touch targets.
- **`frontend/src/components/AdviceCard.jsx`** (Task 9.2):
  - Displays bilingual advice: Bangla message text (`lang="bn"`) guaranteed at least 18 px in Noto Sans Bengali, and English translation text (`lang="en"`).
  - Metadata header: Rule ID badge (`Rule: flood_high_early`), triggering hazard name, and `RiskBadge` with accessible level indicator.
  - Level 2 audio action: Call / Listen audio button with pulse animation during playback and Web Speech API fallback.
  - Accessible empty state for uninitialized inputs.
- **`frontend/src/pages/Simulator.jsx`** (Tasks 9.3, 9.4):
  - Desktop 2-column layout (>=1024 px) with centered PhoneMockup on the left and Advisory Diagnosis side panel on the right; stacked responsive layout (<1024 px).
  - Integrates with backend `/api/sim/sms`, `/api/advice`, and `/api/risk`.
  - Quick-fill buttons (Task 9.4):
    - `SYLHET AMAN` (Flash flood high risk demo)
    - `KHULNA BORO` (Coastal salinity risk demo)
    - `RAJSHAHI AMAN` (Drought risk demo)
    - Plus `HELP` and `STOP` command chips.
  - Advisory Diagnosis side panel:
    - Rule ID chip (e.g. `flood_high_early`).
    - Triggering Hazard and Level with `RiskBadge` (e.g. Flood - High).
    - Underlying scores grid: 3 score cards (Drought, Flood, Salinity) with numeric score (0 to 100) and `RiskBadge`.
    - Embedded `AdviceCard` showing bilingual advice.
    - Simulation Date selector (defaults to demo date `2022-06-16`).
    - Mandatory NASA disclaimer: *"Based on NASA satellite data. Not an official government warning."*
- **Backend enhancements**:
  - `backend/app/schemas.py`: added optional `date: dt_date | None = None` to `SimSmsRequest`.
  - `backend/app/routers/messaging.py`: passed `as_of_date=payload.date` to `handle_inbound_sms`, enabling date-specific SMS simulation for demo dates.
  - `backend/tests/test_api.py`: added `test_sim_sms_with_date_param`.
- **i18n Localization**:
  - `frontend/src/i18n/en.json` & `bn.json`: added complete translation dictionary for `simulator` namespace.
- **Unit Tests**:
  - `frontend/src/__tests__/simulator.test.jsx`: 7 Vitest tests covering AdviceCard (Bangla >=18px in Noto Sans Bengali, English translation, Rule ID, empty state), PhoneMockup (LCD screen, message list, Bangla >=18px, keypad controls), and quick-fill commands.

### Verification

- `pytest`: 147 backend tests pass (18 in `test_api.py`).
- `npm test`: 32 frontend vitest tests pass across 3 test files (7 in `simulator.test.jsx`).
- `npm run build`: Vite production bundle builds in 4.19s with zero errors.
- `POST /api/sim/sms` with `{"from": "+8801700000000", "body": "SYLHET AMAN", "date": "2022-06-16"}` verified:
  - Returns welcome message and flood high advice message in Bangla.
  - Subscriber created with `active=True`.
- Invalid input verified:
  - `POST /api/sim/sms` with `INVALID INPUT` returns help message (`বুঝতে পারিনি। এভাবে লিখুন: SYLHET AMAN`).
- Side panel diagnosis verified:
  - Sylhet 2022-06-16 scores: Drought 0.87 (Low), Flood 98.01 (High), Salinity 0.0 (Low).
  - Triggering hazard: Flood (High).
  - Rule ID: `flood_high_early`.
- Bangla typography verified:
  - `font-size: 18px !important; font-family: var(--font-bangla) !important;` enforced on all Bangla spans with `lang="bn"`.
- Mobile responsiveness:
  - Verified at 360 px width with zero horizontal overflow (`phone-wrapper` max-width 320 px).

## Phase 10 details

Last completed task: 10.6 and docs. Phase 10 is complete.

- `services/nasa/smap.py`: group/variable confirmed from the real file before coding; nearest-cell lookup from 1-D lat/lon vectors; raw granule deleted; per-day JSON cache. CLI `python -m backend.app.services.nasa.smap --date 2022-06-16`.
- `services/nasa/modis.py`: AppEEARS login, point task, poll, bundle CSV, NDVI baseline functions. Three real-API differences found and fixed (303 on done, no `status` key while processing, NDVI already scaled); see `docs/data_sources.md`.
- `pipeline/run_pipeline.py`: soil input is SMAP when present, else POWER (not degraded); `inputs.soil_source`, `inputs.ndvi_anom`, `sources.soil/ndvi`; Observation rows `SMAP_L4/rz_pctl` and `MODIS_MOD13Q1/ndvi`; `PipelineRun.detail.sources.SMAP/MODIS` with fallback reason. SMAP and MODIS never change the run status (Section 7.7).
- `pipeline/build_ndvi_baseline.py` wrote `ndvi_mean` (2003-2020) for all 8 districts; `build_baseline` now preserves it.
- `/api/risk/{id}/explain` adds `soil_source` and `ndvi` (with `fallback`/`used`); `/api/sources` adds SPL4SMGP 008 and MOD13Q1 061.
- Frontend: `config/layers.js` (confirmed ids, real tile matrix sets), `OverlayControl.jsx`, overlay in `RiskMap.jsx`, `SourceNotes.jsx` in `FactorBars.jsx`; fixed the `vegetation_anomaly` label key.
- Decisions in `docs/methodology.md` (Phase 10): salinity without NDVI is `degraded: false` (resolves the earlier F2.2 vs 7.6 note); no `/api/layers` route; extra 16-day NDVI GIBS layer because the 8-day layer starts 2025.
- Not done: snapshot JSON files not re-exported (Phase 12); Phase 10 live rows exist only in the local database.

## Phase 11 details

Last completed task: 11.5. Next task: Phase 12 (not started).

- `services/messaging/tts.py` (11.1): `<sha256(text)>.mp3` in `AUDIO_DIR` (default `data/audio/`, gitignored). Text is registered in a `.txt` sidecar and the MP3 is synthesized with gTTS (`lang="bn"`) on first request, once, under a lock. gTTS is imported only inside `synthesize`.
- `GET /api/audio/{filename}` (11.2): `audio/mpeg`; 404 for unknown or malformed names; 503 with the JSON error body when gTTS fails or `TTS_ENABLED=false` and the MP3 is missing. `POST /api/advice` now returns `audio_url` (null when `TTS_ENABLED=false`).
- Frontend (11.2): `utils/audio.js` plays the MP3 (one clip at a time). The Call button in `Simulator.jsx` and the audio button in `AdviceCard.jsx` use it; on failure they show a text-only notice. The Web Speech fallback was removed. English and Bangla strings added.
- `services/messaging/twilio_gateway.py` and `gateway_loader.py` (11.3): Twilio is imported only by `load_twilio_gateway()` after the `TWILIO_ENABLED` check. `/api/sms/inbound` and `/api/voice/inbound` validate `X-Twilio-Signature` against `PUBLIC_BASE_URL` and return TwiML (`text/xml`); both return 404 while the flag is off. Voice plays the cached MP3 through the public URL.
- `routers/admin.py` (11.4): router-level `X-Admin-Key` dependency (401 if missing, wrong or the configured key is empty); `POST /api/admin/broadcast` with `dry_run` defaulting to true. Live sends use Twilio when enabled, otherwise the in-memory simulator gateway.
- `handler.py`: advice selection extracted into `current_advice()`, shared by SMS registration, voice and broadcast (behaviour unchanged, all earlier tests pass).
- README (11.5): tunnel and webhook steps, broadcast example. Decisions are in `docs/methodology.md` (Phase 11).
- `backend/tests/conftest.py`: autouse fixture isolates `AUDIO_DIR`, `TTS_ENABLED`, `TWILIO_ENABLED` and `ADMIN_API_KEY` from the real `.env`. `test_api.py::test_advice_endpoint` now expects an `audio_url`.
- Not done: `POST /api/admin/pipeline/run` (Section 7.2) is outside the Phase 11 task list. The shipped `ADMIN_API_KEY=change-me` default still authenticates, so set a real key before exposing the app.

## Phase 12 details

Last completed task: A2 (getScoring client). Next task: A3 (Method page rewrite).


