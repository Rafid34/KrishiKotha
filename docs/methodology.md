# Methodology

## Decisions


- Crop stages are stored with `start_month` and `end_month` (inclusive, wrap-around allowed, e.g. Dec to Jan). Where two stages overlap in a month (e.g. Aman Jul is both nursery and transplanting), the later stage in `crops.json` order wins; to be implemented in `stages.py`.
- Percentile rank uses the mid-rank convention for ties: `(below + 0.5 * equal) / n * 100`. This keeps a zero-rain day from scoring 0 or 100 when many baseline samples are zero.
- Rolling sums need a full window (`min_periods = window`); any missing day inside the window gives a missing sum, which is dropped from baseline samples.
- Baseline day-of-year window is circular on a 366-day year, plus or minus 15 days. Day-of-year numbers are used as is, so in non-leap years dates after 28 Feb are one day off versus leap years (a 1-day shift, well inside the 31-day window).
- Baseline files store the full sorted samples (about 620 values per sample per day of year), rounded (rain to 0.1 mm, soil wetness to 0.001) and written compactly. This is about 3.2 MB per district, 25 MB for all eight.
- Baseline `ndvi_mean` is left null until Level 2.
- POWER requests use one call per district for the full 2001-2020 range. Raw responses are cached under `data/cache/power/` (gitignored).
- IMERG raw granules are downloaded into a `tempfile.TemporaryDirectory`, so they are deleted as soon as the clipped file is written (and on any failure). Only `data/cache/imerg/{run}_{YYYYMMDD}.nc` (about 22 KB each) is kept.
- District rainfall is the plain mean of non-null 0.1 degree cells whose centres fall inside centroid plus or minus 0.25 degrees (no area weighting; cells are about 11 km square). A box with no valid cell gives null.
- `accumulate()` reads only the cache, never the network. A day with no cached file or an all-null box counts as missing; the total sums the days that are available and is null when none are.
- `fetch_day()` checks that the granule's `time` matches the requested date and fails loudly otherwise. It downloads the first search result only.
- When `soil_pctl` is missing in `score_flood` and `score_drought`, the remaining weights are proportionally re-normalized (0.40/0.75 and 0.35/0.75 for flood; 0.35/0.55 and 0.20/0.55 for drought) and `degraded` is set to `True`.
- Salinity formula without NDVI is the documented Level 1 baseline and has `degraded: False`; `degraded` can be overridden when an expected Level 2 NDVI task fails. When `coastal_distance_km >= 150`, `s_coast` clamps to 0, yielding 0 salinity risk.
- If `b30_mean` is 0 (extremely dry baseline), rain deficit defaults to 0 to prevent division by zero.


## Phase 5 decisions (pipeline, snapshots, read API)

- Scoring a date range needs history: for `--start S` the pipeline fetches IMERG from `S - 29 days` so that `R30` is a full 30-day sum on the first scored date. For 2022-05-15 that means IMERG from 2022-04-16. Lookback days are cached but get no risk rows or observations.
- A district and date is scored only when all of its 3, 7 and 30 day IMERG windows are complete; otherwise it is skipped, listed in `PipelineRun.detail.skipped`, and the run status is `partial` (or `failed` if nothing was scored). Gaps are never filled with zeros.
- POWER soil wetness uses the latest `GWETROOT` value on or before the effective date; `stale_days` is stored in `risk_snapshots.inputs` and `sources.soil`. `Tmax7` is the mean of the non-null `T2M_MAX` values in the 7 days ending on that date. If no `Tmax7` exists, the drought heat term is 0 and the snapshot is flagged `degraded` (also recorded as `inputs.tmax_missing`). Missing soil follows the Phase 4 reweighting and `degraded` rule.
- Run status: `ok` when IMERG and POWER succeeded for every district and date, `partial` when some failed but rows were written, `failed` when nothing was written. The CLI exits 0 only for `ok`.
- Each IMERG day is tried 3 times (3 s, 6 s backoff). After 5 days fail in a row the run stops fetching and marks the remaining days failed. This was added after a transient `ConnectionError` during Earthdata login aborted the first Final Run attempt.
- Each stored score input carries `source` and `data_date` so `/api/risk/{id}/explain` is a plain read of the stored JSON, with no recomputation.
- Observations written per district and date: `precip_mm` (IMERG, `IMERG_FINAL` or `IMERG_LATE`, version `V07`), `tmax_c` and `soil_wetness` (POWER, version label `V2`, the API major version; the response header reports 2.10.0). Values are null when the source has none for that exact date.
- Snapshot files are self-contained (risk rows, observations and the matching `PipelineRun`). `sylhet_2022.json` is named for the event but holds all eight districts for 2022-05-15 to 2022-06-30, so the replay can colour the whole map and `/api/risk?date=2022-06-16` returns 8 districts in snapshot mode. `latest_30d.json` holds the 30 newest dates in the database.
- Snapshot mode (`DATA_MODE=snapshot`) loads `data/snapshots/*.json` into the database at startup and an `ensure_online()` guard in the POWER, CMR, Earthdata and IMERG clients raises `OfflineModeError` before any request is made. Re-loading is an idempotent upsert.
- `/api/sources` takes `last_data_date` from stored observations, never from a live CMR call, so it works offline. The spec also says `/api/sources` echoes the scoring constants (Section 7.6) while Section 7.2 defines its response as a plain list of datasets; the list shape was kept and the constants (`SCORING_CONSTANTS`) are not exposed yet. This needs a decision for the Method page in Phase 12.
- `/api/risk/{id}` anchors its window on the district's newest snapshot date, so with both the 2022 event and recent data loaded, `days=365` does not reach 2022. The event series is served by `/api/backtest/sylhet-2022` (Phase 12).
- Error format: every route, including framework 404/405/422 responses, returns `{"error": {"code", "message"}}`.
- Response extras beyond the Section 7.2 examples: `/explain` returns all three hazards (flood, drought, salt), each with `level`, and each input also has `raw`.
- Observed behaviour worth revisiting in Phase 12: IMERG rainfall (mm) is scored against a POWER `PRECTOTCORR` baseline, two different products. Sylhet flood is already 96 on 2022-05-15 (a real mid-May flood) and stays above 60 for the whole period, so the "first moderate" date for the backtest may fall well before June.

## Phase 6 decisions (advice engine, parser, SMS simulator API)

- Overlapping crop stages: Where two stages overlap in a month (e.g. Aman in July is in both nursery and transplanting), the later stage in `crops.json` order wins (`transplanting`). If a date falls outside all stages, stage is `off_season` with 0.7 sensitivity for all hazards.
- High drought advice for non-Aman / other stages: The spec defines `drought_high_transplant` specifically for Aman rice in nursery or transplanting stages. When drought effective score is High (>= 70) for other crops (Boro, Aus) or other growth stages, advice falls back to `drought_moderate_any` to ensure farmers receive irrigation guidance rather than incorrectly receiving `none_low`.
- Inbound SMS simulator replies and logging: For registration requests (`<DISTRICT> <CROP>`), the simulator returns two replies: `welcome` and the hazard advice for the latest district snapshot. Both outbound replies are logged in `message_logs` (direction `out`, channel `sim`), creating exactly two `message_logs` rows.
- 134-character limit: Enforced strictly in `composer.py` on Unicode NFC-normalized Bangla text (`text_bn`). Any rendered string exceeding 134 characters raises `MessageLengthExceededError`.
- Message wording: All templates describe observed conditions only (past rainfall, soil moisture, dry soil) and contain no forecast claims.

## Phase 8 decisions (district detail, event replay and backtest)

- Reference flood onset date: 2022-06-16.
- Public citations for reference onset:
  1. Flood Forecasting and Warning Centre (FFWC), Bangladesh Water Development Board (BWDB), *Annual Flood Report 2022*, Section 4 (Surma-Kushiyara Basin flood hydrographs: rivers crossed danger levels rapidly between 15-16 June 2022, causing catastrophic inundation of Sylhet and Sunamganj on 16 June 2022).
  2. UN OCHA / ReliefWeb: "Bangladesh: Floods - Jun 2022" (ReliefWeb Situation Report, 17 June 2022: heavy monsoon flash floods inundated northeastern districts with severe impact starting 16 June 2022).
- Derivation of the five replay step dates from data (Section 9 task 8.4):
  - Step 1 ("Rain begins"): first day rainfall exceeds the 50th baseline percentile of the 3-day sum (`rain3_pctl > 50`) -> `2022-05-15`.
  - Step 2 ("Rain builds"): first day `f_rain7` is at least 60 (`rain7_pctl >= 60`) on or after Step 1 -> `2022-05-15`.
  - Step 3 ("Heavy rain"): first day flood level is Moderate (`flood_level == "moderate"`, score 40–69.99) on or after Step 2 -> `2022-05-25`.
  - Step 4 ("Extreme rain"): first day flood level is High (`flood_level == "high"`, score >= 70) on or after Step 3 -> `2022-06-02`.
  - Step 5 ("Flood"): reference onset date -> `2022-06-16`.
- First Moderate and High milestone dates: `first_moderate = 2022-05-25`, `first_high = 2022-06-02`.
- Measured lead time: 14 days (`2022-06-16` minus `2022-06-02`), exceeding the 3-day target without threshold tuning.
- Fixed thresholds: As required by Sections 8.4, 9, 10.4 and 13, all thresholds (<40 Low, 40-69.99 Moderate, >=70 High; weights 0.40/0.35/0.25) were fixed in advance and were not tuned to fit the Sylhet 2022 event.


## Phase 10 decisions (SMAP, MODIS NDVI, GIBS overlays)

- **Soil input preference.** `score_district_day` passes the SMAP `sm_rootzone_pctl` value to the scoring engine as `soil_pctl` when it is available for that district and day. Otherwise the POWER `GWETROOT` value is percentile-ranked against the baseline as before. Falling back from SMAP to POWER is not `degraded` (Section 4 F2.1 only asks that the UI show the fallback source). `degraded` is set only when neither source has a value (the existing Section 7.6 missing-soil rule). The choice is stored per snapshot in `inputs.soil_source` (`SMAP_L4` or `POWER_GWETROOT`), in `sources.soil`, and in the `source` field of the `soil_pctl` input.
- **SMAP per district.** Each district uses the single nearest 9 km cell to its centroid. Where that cell is water or masked (fill value -9999), that district falls back to POWER while the others still use SMAP. Observed on 2026-10-10: Sunamganj, Khulna and Barishal cells were fill values.
- **SMAP failures never change the pipeline status.** Section 7.7 only requires IMERG and POWER for exit code 0, so SMAP and MODIS failures are recorded under `PipelineRun.detail.sources.SMAP` and `.MODIS` but cannot make a run `partial` or `failed`.
- **Salinity without NDVI is `degraded: false`.** F2.2 and Section 7.6 agree: a pending or failed NDVI task selects the documented Level 1 formula and `degraded` stays false. This resolves the contradiction noted in the Phase 5 patch (the earlier worry came from reading `degraded: true` into F2.2). The fallback is still shown in the UI through `explain.ndvi.used = false`.
- **NDVI baseline (2003-2020).** `python -m pipeline.build_ndvi_baseline` submits one AppEEARS point task (MOD13Q1.061 `_250m_16_days_NDVI`, 2003-01-01 to 2020-12-31, 8 centroids), averages each of the 23 composites across years, expands them to every day-of-year and writes `ndvi_mean` into `data/baseline/{district}.json` and the `baselines` table. The anomaly is the current NDVI minus the baseline at the day-of-year of the composite the value came from (not of the scored day). If the baseline or the current NDVI is missing, the anomaly is `None` and salinity uses the Level 1 formula. Rebuilding the POWER baseline keeps `ndvi_mean` (`merge_ndvi_mean`).
- **One NDVI fetch per pipeline run.** The NDVI value is a 16-day composite, so a single AppEEARS lookup per run is applied to every scored day. A pending task is remembered in `data/cache/modis/pending_tasks.json` and reused by the next run instead of submitting a duplicate; a finished task is cached in `data/cache/modis/{start}_{end}.json`.
- **NDVI scale.** AppEEARS returns NDVI already scaled (for example 0.4311), so no scale factor is applied; values outside -0.2 to 1.0 (fill is -0.3) are dropped. Quality flags (`VI_Quality`) are not used.
- **Fallback product VNP13A1.002** (layer `500_m_16_days_NDVI`, ids confirmed in the AppEEARS catalogue) is only tried if the MOD13Q1 task cannot be submitted; it has never been exercised.
- **GIBS NDVI layer.** The overlay menu offers `MODIS_Terra_L3_NDVI_16Day` (coverage from 2000) as well as the spec's `MODIS_Terra_NDVI_8Day` (coverage only from 2025-02-12), because the 8-day layer has no imagery for the 2022-06-16 demo date. The UI checks coverage first and explains the missing imagery instead of showing an empty map.
- **No `/api/layers` route.** Section 7.2 lists it, but the Phase 10 file list gives the layer configuration to the frontend (`frontend/src/config/layers.js`, F2.6), so no backend route was added.
- **Snapshots not re-exported.** `data/snapshots/*.json` still hold the Phase 5 rows (POWER soil, no `soil_source`). `/api/risk/{id}/explain` returns `soil_source: null` and `ndvi: null` for them and the UI shows no source note. Phase 12 re-exports the snapshots with SMAP-aware rows.
