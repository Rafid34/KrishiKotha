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

