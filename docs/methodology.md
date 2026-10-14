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

