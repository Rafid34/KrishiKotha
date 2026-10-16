# CORRECTIONS.md: Krishi Kotha correction phases

Source: REVIEW_REPORT.md (review of Phases 0 to 12), triaged. Put this file in the repository root next to PROGRESS.md. Run one section per chat.

## Common rules (apply to every section)

1. Read only: this "Common rules" section, the one section you were told to run, and the files it names. Never open `data/baseline/*.json`, `data/snapshots/*.json` or `data/cache/*` unless a task names them. Read `PROJECT_SPEC.md` only by line range.
2. Start with: `git status --short` and `git log --oneline -3`.
3. Do not change scoring weights, thresholds, baselines or formulas. Section C4 is the only place where a preprocessing change is allowed, and only after the user approves it.
4. Commit after every task: `fix C<n> <finding ids>: <what>`. After each commit, append one line under a `## Corrections` heading in PROGRESS.md: finding id, status (FIXED, NOT REPRODUCED, DEFERRED), and the command that proves it.
5. A finding that cannot be reproduced gets status NOT REPRODUCED. Change no code for it.
6. No questions. Paste the exact output of every verification command. Keep replies to one line per action.
7. Never print or ask for credentials. Write Bangla and other non-ASCII text only with the file-edit tool, never with PowerShell `Set-Content` or `Out-File`.
8. Never commit `.env`, `*.db`, `data/cache/` or `data/audio/`.

## Triage of the review (read before starting)

| Finding | Reviewer rating | Triage |
|---|---|---|
| R-008, R-023 | HIGH, "document it" | Under-rated. They show the flood score is High in January and the drought seasonality check fails. The 32-day lead time is not evidence of skill. Diagnose first (C0). |
| R-003 | BLOCKER | Valid, but the suggested colour `#B07D00` gives 3.63:1, not 4.53:1. Compute it yourself (C1). |
| R-001, R-002 | BLOCKER | Deliberate omissions recorded in Phases 10 and 11. Real spec gaps but not demo blockers (C2). |
| R-012 | MEDIUM | Probably a false positive. `main()` returns 0 only when status is ok and `sys.exit(main())` is used. Verify, do not change (C2). |
| R-013, R-015, R-017 | LOW, LOW, HIGH | The reviewer did not verify them ("NOT VERIFIED", no evidence). Verify first (C2). |
| R-019 | MEDIUM | Suggested fix is wrong: `aria-live` is for content that changes. Use a static description (C1). |
| R-022 | MEDIUM | The citations were written by an earlier agent session and were never opened. Treat as unverified (C5). |
| R-005, R-006, R-024 | BLOCKER, HIGH, LOW | Phase 13 tasks, not defects. Not in this file. |
| Section 8.3 table | n/a | Unreliable ("15 tests pass" matched against 202 is meaningless). Ignore it. |

---

## C0: Diagnose the flood and drought seasonality failure (READ-ONLY)

Do not edit any project code, baseline, snapshot or database. Write only `DIAGNOSIS.md` and scratch files under `data/cache/diag/`. Everything runs offline from existing caches.

Facts to explain (from the review, verify them first):
- Sylhet mean flood score in January 2022 is 73.34 (High) in `data/cache/validation_2022.db`.
- Sylhet first High is 2022-05-15, the first scored day. The 32-day lead time is therefore limited by where the window starts, not measured from a real first crossing. There are 22 High days before the onset.
- The Rajshahi drought check fails: July mean 76.4 is above March 26.1 and April 64.5.

Tasks:
- D1. Monthly table for Sylhet, 2022, from `risk_snapshots` (`inputs` JSON): number of High flood days; mean `rain3_pctl`, `rain7_pctl`, `soil_pctl`; mean `r3` and `r7` (mm); median of the baseline 3-day and 7-day samples for the matching day of year; share of baseline samples equal to 0.
- D2. Monthly table for Rajshahi drought: mean `d_soil`, `d_rain`, `d_heat` (the input values), `r30` against `rain30_baseline`, and `soil_pctl`.
- D3. Product mismatch. For Sylhet and Rajshahi in 2022 compare IMERG district-box daily rain (from the cache, via `imerg.accumulate` or `district_means`) with POWER `PRECTOTCORR` at the centroid (cache hit only, no network). Report, per month: totals for both; number of days equal to 0 and number with 0 < rain < 1 mm. Report whether July 2022 total for Rajshahi is below the 2001 to 2020 POWER July mean (separates a real dry year from a product artifact).
- D4. Code check. Print `percentile_rank` and the baseline rolling-sum code. Run a synthetic test: value 0 against a sample that is 70 percent zeros must give 35.0. Confirm baseline 3, 7 and 30 day sums end on the date, the same definition as live `rain_sums`.
- D5. Offline what-if with one rule fixed in advance: a wet day is daily rain of at least 1.0 mm, otherwise 0, applied identically to the POWER baseline (2001 to 2020, cached) and to live IMERG. Do not try any other value. Compute in a scratch script only: Sylhet monthly High-day counts, the lead-time block, and the four seasonality checks (pass or fail).
- D6. Write `DIAGNOSIS.md`: root cause with evidence (bug, product mismatch, real climate anomaly, or design limit); the D5 results next to the current ones; an options table: A wet-day threshold (applied to both sides); B IMERG-based baseline (state the number of daily files to download and a time estimate; suggest a shorter period such as 2015 to 2021); C keep as is and document the limitation. Give a recommendation. Apply nothing.

Verification: `git status --short` shows only `DIAGNOSIS.md` as new (scratch files are under the ignored cache). Commit `DIAGNOSIS.md` as `C0: diagnosis`.

---

## C1: Frontend fixes (R-003, R-004, R-010, R-018, R-019, R-020, plus the censored lead-time guard)

- F1 (R-003) Contrast. Write `scripts/check_contrast.py` that computes WCAG ratios for every text and background pair actually used in `frontend/src` CSS and JSX (find them with grep on `var(--`), and for non-text marker colours against their neighbours (3:1). Fix failures only by adding darker variants, such as `--risk-moderate-text`, and use dark ink text on the amber fill. Reference values: `#E0A100` on white is 2.27 and on `#F7F6F1` is 2.09; dark ink `#1F2A24` on `#E0A100` is 6.55; `#8F6600` on white is 5.16 and on `#F7F6F1` is 4.77; `#B07D00`, suggested by the review, is only 3.63 so do not use it for text. The script exits 1 on any failing pair.
- F2 (R-004) Disclaimer. Show `t('disclaimer')` on the Dashboard at all times (not only inside `DistrictPanel`). Confirm Replay, Simulator and Method also show it. Add one vitest per page that renders the page and finds the text.
- F3 (R-010) Encoding. Write `scripts/check_encoding.py`: read every file from `git ls-files` that is text, as UTF-8, and report any occurrence of `â€`, `Ã`, `à¦`, `à§`, `Â` or U+FFFD, with file and line. Exit 1 on hits. Fix each hit with the correct character (for example the em dash) using the file-edit tool. Includes `RiskMap.jsx:156` and the JSX comments. Also check that no file has a BOM.
- F4 (R-019) Chart summaries. For every chart (`TrendChart`, `EventReplay`) render a static paragraph generated from the data (for example total rainfall, peak day and value, range of soil wetness) in both languages, and link it with `aria-describedby` from the chart container, which gets `role="img"`. Do not use `aria-live`. Strings go in `en.json` and `bn.json`. Tests check the generated text.
- F5 (R-020) Error states. List every API call in `frontend/src` and what the page shows on failure and while loading. Add a visible error banner with a Retry button to each that lacks one, starting with `getDistricts()` in `Dashboard.jsx`. Add one test that mocks a failing districts fetch.
- F6 (R-018) Default date. Remove the `DEMO_DATE` constants from `Dashboard.jsx` and `Simulator.jsx`. Default to the `date` returned by `GET /api/risk` without a date parameter. Add a quick-pick button "June 2022 flood demo" that sets 2022-06-16. Tests: default comes from the API; the button sets 2022-06-16. Record in PROGRESS.md that the demo script must press that button.
- F7 (censored lead time) In `EventReplay.jsx` and the data it gets: when `first_high` equals the first date of the series, do not show "Warning came N days before the flood". Show that flood risk was already High on the first day of the window (2022-05-15) and that the lead time is therefore at least N days, measured from the window start. Both languages. Test both cases.

Verification (paste outputs): `cd frontend; npm test; npm run build`; `.\.venv\Scripts\python.exe scripts\check_contrast.py`; `.\.venv\Scripts\python.exe scripts\check_encoding.py`; `git grep -n "DEMO_DATE" -- frontend/src` must print nothing.

---

## C2: Backend and configuration fixes (R-001, R-002, R-009, R-012, R-013, R-014, R-015, R-016, R-017, R-025)

- B1 (R-012) Verify before changing. Run `$env:DATA_MODE='snapshot'; .\.venv\Scripts\python.exe -m pipeline.run_pipeline --start 2022-05-15 --end 2022-05-16; echo $LASTEXITCODE` (expect 2). Add a unit test that calls `main()` with `run_pipeline` monkeypatched to return a record with status `partial` and one with `ok`, asserting exit codes 1 and 0. If both pass, record R-012 as NOT REPRODUCED and change no code.
- B2 (R-001) Add `GET /api/layers` returning the GIBS layer definitions (id, title, tile matrix set, format, coverage start). Add a pytest that reads `frontend/src/config/layers.js` as text and asserts every layer id and matrix set returned by the route appears in it. Record under Decisions that the frontend keeps its own copy.
- B3 (R-002) Add `POST /api/admin/pipeline/run`, protected by the existing `X-Admin-Key` dependency. Body: `{"mode":"live","as_of":"YYYY-MM-DD","run":"late"}` (`as_of` optional, default newest IMERG day; start is `as_of` minus 29 days). Behaviour: insert a `PipelineRun` row with status `running` and return `{"run_id": id, "status": "started"}` immediately; run the pipeline in a background thread that updates that same row (add an optional `record_id` argument to `run_pipeline`; no other change to it); return 409 when a run is already active; return 409 when `DATA_MODE=snapshot` and mode is `live`. Tests use an injected fake runner, never the network.
- B4 (R-009) Admin key. Outside `APP_ENV=development`, treat `ADMIN_API_KEY` values `""` and `change-me` as unset (every admin route returns 401) and log one startup warning. Add a comment in `.env.example` showing `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Existing tests must still pass.
- B5 (R-017, R-025) Settings parity. Run `git grep -n -E "PHONE_HASH_SALT|APPEEARS_API_BASE|GIBS_WMTS_BASE|os\.getenv|os\.environ" -- backend pipeline scripts` and report how each is read today. Declare the three variables in `Settings`, use them where the values are currently hard-coded or read directly, and hash phone numbers as `sha256(salt + phone)` (note that existing demo subscribers keep working because lookup also uses `phone_e164`; state what you did). Add `backend/tests/test_env_parity.py` asserting that every key in `.env.example` is a `Settings` field or in an explicit allowlist (`VITE_*`), and every `Settings` field is in `.env.example`.
- B6 (R-013) Add a test for the circular day-of-year window: the window for day 1 contains days 351 to 366 and 1 to 16; the window for day 366 contains 351 to 366 and 1 to 16 minus the same count symmetric. Fix the code only if the test exposes a bug.
- B7 (R-015) Add `backend/tests/test_static_vs_spec.py` with the expected district values (coordinates, coastal distance, names, division) and the crop stage table typed from `PROJECT_SPEC.md` lines 601 to 629, asserting `data/static/districts.json` and `crops.json` equal them.
- B8 (R-014) Add `backend/tests/test_cmr.py` using `respx`: normal response, empty result, HTTP error.
- B9 (R-016) Parser: treat `-`, `_`, `,` and `/` like whitespace. Tests for `Sylhet-Aman`, `sylhet,aman`, `SYLHET/AMAN`, plus Bangla `সিলেট-আমন`.

Verification: `.\.venv\Scripts\python.exe -m pytest -q` (paste the totals); `.\.venv\Scripts\python.exe scripts\check_env.py`; `.\.venv\Scripts\python.exe scripts\verify_offline.py`.

---

## C3: Dependencies and live smoke test (R-011, plus unverified checklist items)

- N1 (R-011) Run `cd frontend; npm audit --omit=dev` and `npm audit` (full). Run `npm audit fix` without `--force`; rerun tests and build. If a `react-router` advisory remains, read its description: if it affects only framework or server-rendering modes (this app uses `BrowserRouter` and `Routes` only), record it as an accepted risk under "Security notes" in `docs/methodology.md` with the advisory ids. If a version 7 upgrade is a drop-in, try `npm install react-router-dom@7` on a git branch; keep it only if `npm test` and `npm run build` both pass, otherwise revert. Do not use `--force`.
- N2 Live checks (network and Earthdata credentials from `.env`; never print them): run `.\.venv\Scripts\python.exe scripts\verify_endpoints.py`. Then a three-day live pipeline into a scratch database: set `$env:DATABASE_URL` to a file under `data/cache/smoke.db`, compute the dates (newest IMERG day and the two days before) and run `pipeline.run_pipeline --start <d-2> --end <d> --run late`. Expect status ok and 24 `risk_snapshots` rows (8 districts by 3 days). Delete the scratch database afterwards. Record both results in PROGRESS.md as the evidence for Section 10.2.

Verification: paste the `npm audit --omit=dev` summary line, the `verify_endpoints.py` result lines and the row count query.

---

## C4: Methodology fix and re-validation (GATED: run only after the user has read DIAGNOSIS.md and chosen Option A)

If the user chose B or C, stop and tell them this section does not apply.

The wet-day threshold of 1.0 mm/day was fixed in advance (standard wet-day definition). Do not try other values and do not tune.

- A1. Add `WET_DAY_MM = 1.0` and a helper that sets daily rain below it to 0. Apply it identically in (a) the baseline build, before the 3, 7 and 30 day sums; (b) the live district daily rain before `rain_sums` in `run_pipeline`. Add `"preprocessing": {"wet_day_mm": 1.0}` to `SCORING_CONSTANTS` and show it on the Method page. Patch `PROJECT_SPEC.md` Section 7.6 with a one-line preprocessing note (edit only that line range).
- A2. Rebuild baselines offline: `.\.venv\Scripts\python.exe -m pipeline.build_baseline` (POWER cache). Confirm `ndvi_mean` is preserved.
- A3. Back up `data/krishi_kotha.db` to `data/cache/` first. Rerun, all from caches: `pipeline.run_pipeline --start 2022-05-15 --end 2022-06-30 --run final`; delete `data/cache/validation_2022.db` and run `pipeline.validate run-year`. Rebuild snapshots (`pipeline.build_snapshot`), then run `scripts/verify_offline.py`.
- A4. Extend `pipeline/validate.py` report with a negative control: High flood days in December to February for Sylhet, Sunamganj and Rangpur, and the share of all High days per month for Sylhet. Add a unit test.
- A5. Update tests that depend on baselines or expected values. Write a before and after table in `docs/methodology.md` (old numbers from the existing block, new numbers from the report). State plainly whether the seasonality checks now pass, and state that no threshold other than 1.0 mm was tried. Update every other place that quotes the old lead time or counts (`PROGRESS.md`, frontend text, tests, docs).

Verification: pytest totals, `npm test`, `npm run build`, `verify_offline.py`, and the full validation report printed.

---

## C5: Documentation honesty (R-007, R-021, R-022; run after C4)

- H1 (R-007) In PROGRESS.md leave history intact. Where a number was superseded (Phase 8 "14 days"), append "(superseded, see Phase 12 and C4 details)". Make sure the current numbers in the Phase 12 and C4 sections match the latest report exactly.
- H2 (R-021) In `docs/methodology.md` add "Operational relevance": the backtest used the IMERG Final Run (gauge-adjusted; CMR newest Final granule is about a year old), while the live service uses the Late Run (about 14 hours latency, not gauge-adjusted). If network time allows, repeat the event backtest with `--run late` for 2022-05-15 to 2022-06-30 into a scratch database (about 76 daily files) and report both side by side; if Late granules for 2022 are unavailable, say so.
- H3 (R-022) Verify the reference flood citations. The current text in `docs/methodology.md` and `REFERENCE_ONSET_CITATION` in `backend/app/services/backtest.py` (FFWC Annual Flood Report 2022 "Section 4", ReliefWeb situation report 17 June 2022) was written by an earlier session and was never checked. Use the browser or search tool to open real sources. Record title, publisher, URL, publication date and the exact statement that supports the onset date. Do not rely on memory. If a source cannot be opened, mark it UNVERIFIED in both places and describe the onset date as an assumption. If the sources support a different onset date, change `REFERENCE_ONSET_DEFAULT`, rerun the report, and record before and after.
- H4. List any other factual claim in `docs/methodology.md` and `docs/data_sources.md` that has no measured number or source behind it, and mark each as an assumption.

Verification: `pytest -q`; `git diff --stat` shows only docs, PROGRESS.md and the citation constant (plus the onset constant if it changed).

---

## RECHECK (run last, in a fresh chat; READ-ONLY except RECHECK.md)

Run: `pytest -q`; `cd frontend; npm test; npm run build; npm audit --omit=dev`; `scripts\check_contrast.py`; `scripts\check_encoding.py`; `scripts\verify_offline.py`; `git status --short`. Write `RECHECK.md`: a table R-001 to R-025 with status (FIXED, NOT REPRODUCED, DEFERRED, OPEN) and one line of evidence each, then the three highest remaining risks to the demo. Do not fix anything.
