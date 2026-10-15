# Root-Cause Diagnosis: Flood and Drought Seasonality Anomalies (C0)

Date: 2026-10-15  
Status: READ-ONLY DIAGNOSIS COMPLETE (No project code, baseline, snapshot, or database modified)

---

## 1. Executive Summary & Facts Verified

Review findings R-008 and R-023 were verified against `data/cache/validation_2022.db` prior to diagnosis:
1. **Sylhet January Flood False Alarms (R-008):** Mean flood score in January 2022 is **73.35** (High alert level). There are **21 High flood days out of 31 days** in January, despite a mean 3-day rainfall of only 1.64 mm.
2. **Sylhet Lead Time Censoring (R-008):** The first scored High flood day is **2022-05-15** (score 96.16), which is the very first day of the scored event window (`EVENT_START`). The reported 32-day lead time to the 2022-06-16 reference onset is truncated by the window start, with **22 High flood days before the onset**.
3. **Rajshahi Drought Seasonality Inversion (R-023):** The Section 10.4 drought seasonality check fails because the July 2022 monthly mean drought score is **76.4**, substantially higher than March (**26.1**) and April (**64.5**).

---

## 2. Evidence and Task Outputs (D1 to D5)

### Task D1: Sylhet 2022 Monthly Table (Inputs & Baseline Samples)

Computed from `risk_snapshots` inputs JSON in `data/cache/validation_2022.db` and `data/baseline/sylhet.json`:

| Month | Days | High Days | Mean r3 (mm) | Mean r7 (mm) | Mean rain3_pctl | Mean rain7_pctl | Mean soil_pctl | B3 Med (mm) | B7 Med (mm) | B3 Zero% | B7 Zero% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Jan | 31 | 21 | 1.64 | 3.94 | 73.5 | 75.8 | 69.7 | 0.00 | 0.00 | 74.6% | 54.7% |
| Feb | 28 | 11 | 4.37 | 9.78 | 60.4 | 66.1 | 85.0 | 0.02 | 0.60 | 60.1% | 40.1% |
| Mar | 31 | 0 | 2.92 | 5.66 | 30.3 | 24.1 | 69.7 | 2.21 | 8.65 | 32.2% | 13.7% |
| Apr | 30 | 11 | 34.89 | 75.68 | 56.0 | 56.8 | 91.7 | 22.76 | 58.56 | 7.7% | 1.4% |
| May | 31 | 18 | 77.22 | 181.24 | 62.2 | 66.0 | 89.9 | 39.12 | 95.95 | 2.1% | 0.2% |
| Jun | 30 | 22 | 134.52 | 301.72 | 72.1 | 77.5 | 91.1 | 49.02 | 132.63 | 0.0% | 0.0% |
| Jul | 31 | 1 | 44.36 | 114.78 | 42.5 | 43.1 | 61.8 | 48.10 | 118.93 | 0.0% | 0.0% |
| Aug | 31 | 0 | 31.41 | 72.36 | 31.8 | 24.2 | 36.2 | 43.71 | 109.38 | 0.0% | 0.0% |
| Sep | 30 | 8 | 45.75 | 113.79 | 59.8 | 62.4 | 70.5 | 30.30 | 84.17 | 1.1% | 0.1% |
| Oct | 31 | 12 | 29.45 | 69.33 | 60.1 | 66.0 | 75.6 | 7.67 | 32.93 | 20.0% | 6.1% |
| Nov | 30 | 0 | 0.02 | 0.05 | 36.4 | 26.4 | 78.0 | 0.01 | 0.58 | 64.3% | 40.9% |
| Dec | 31 | 4 | 0.08 | 0.14 | 45.0 | 38.2 | 75.5 | 0.00 | 0.00 | 77.7% | 59.6% |

**Key findings:**
- In January, **74.6%** of the baseline 3-day rainfall samples and **54.7%** of 7-day samples are exactly `0.0 mm`. The baseline median rainfall is `0.00 mm`.
- Mean actual rainfall in January 2022 was only `1.64 mm` over 3 days, yet `rain3_pctl` averaged `73.5` and `rain7_pctl` averaged `75.8`. Combined with `soil_pctl` of `69.7`, the flood score averaged `73.5 * 0.40 + 75.8 * 0.35 + 69.7 * 0.25 = 73.35`, producing 21 High flood warning days during the dry season.

---

### Task D2: Rajshahi 2022 Monthly Drought Table

Computed from `risk_snapshots` inputs JSON in `data/cache/validation_2022.db`:

| Month | Days | Mean Score | Mean d_soil | Mean d_rain | Mean d_heat | Mean r30 (mm) | Mean b30 (mm) | Mean soil_pctl |
|---|---|---|---|---|---|---|---|---|
| Jan | 31 | 5.5 | 12.0 | 0.0 | 0.6 | 14.8 | 6.1 | 88.0 |
| Feb | 28 | 2.2 | 4.8 | 0.0 | 0.0 | 35.4 | 9.4 | 95.2 |
| Mar | 31 | 26.1 | 11.3 | 54.0 | 10.6 | 12.8 | 17.9 | 88.7 |
| Apr | 30 | 64.5 | 50.8 | 95.8 | 40.5 | 9.6 | 52.6 | 49.2 |
| May | 31 | 13.2 | 24.5 | 2.3 | 7.0 | 150.3 | 115.9 | 75.5 |
| Jun | 30 | 34.9 | 40.8 | 44.1 | 5.4 | 121.5 | 189.6 | 59.2 |
| Jul | 31 | 76.4 | 91.3 | 77.3 | 41.2 | 97.8 | 259.5 | 8.7 |
| Aug | 31 | 51.2 | 91.5 | 14.7 | 24.5 | 218.6 | 247.6 | 8.5 |
| Sep | 30 | 30.1 | 61.4 | 2.8 | 7.6 | 249.3 | 214.8 | 38.6 |
| Oct | 31 | 36.7 | 51.2 | 33.7 | 9.1 | 140.4 | 187.8 | 48.8 |
| Nov | 30 | 52.6 | 50.6 | 80.8 | 7.8 | 23.0 | 60.7 | 49.4 |
| Dec | 31 | 62.3 | 50.3 | 100.0 | 23.1 | 0.1 | 7.8 | 49.7 |

**Key findings:**
- In July 2022, Rajshahi received only **97.8 mm** of rain over trailing 30-day windows against a climatological baseline expectation of **259.5 mm** (`rain_deficit` averaged 62%, `d_rain` = 77.3).
- Root-zone soil moisture collapsed to the **8.7th percentile** (`soil_pctl` = 8.7, `d_soil` = 91.3).
- Heat anomaly was severe (`d_heat` = 41.2, or +1.65°C anomaly).
- The drought formula (`0.45 * d_soil + 0.35 * d_rain + 0.20 * d_heat`) correctly scored `76.4` (High drought alert).

---

### Task D3: Product Mismatch (IMERG vs. POWER at Centroid)

Compared IMERG Final Run district-box mean against POWER `PRECTOTCORR` at the centroid from existing disk caches (zero network calls):

#### Sylhet (2022)
| Month | IMERG Total (mm) | POWER Total (mm) | IMERG Zero Days | IMERG 0<R<1 mm | POWER Zero Days | POWER 0<R<1 mm |
|---|---|---|---|---|---|---|
| Jan | 17.0 | 30.6 | 16 | 12 | 15 | 12 |
| Feb | 40.8 | 53.9 | 18 | 6 | 13 | 8 |
| Mar | 38.8 | 135.3 | 22 | 1 | 21 | 2 |
| Apr | 368.6 | 635.6 | 3 | 3 | 0 | 2 |
| May | 801.9 | 1025.9 | 1 | 2 | 0 | 3 |
| Jun | 1352.0 | 1554.0 | 0 | 0 | 0 | 0 |
| Jul | 445.6 | 540.7 | 0 | 1 | 0 | 0 |
| Aug | 322.1 | 423.0 | 0 | 4 | 0 | 3 |
| Sep | 434.7 | 601.0 | 0 | 4 | 0 | 2 |
| Oct | 303.2 | 403.9 | 7 | 7 | 6 | 9 |
| Nov | 0.2 | 1.0 | 28 | 2 | 23 | 7 |
| Dec | 0.8 | 7.8 | 29 | 2 | 27 | 1 |

#### Rajshahi (2022)
| Month | IMERG Total (mm) | POWER Total (mm) | IMERG Zero Days | IMERG 0<R<1 mm | POWER Zero Days | POWER 0<R<1 mm |
|---|---|---|---|---|---|---|
| Jan | 14.4 | 20.9 | 18 | 10 | 18 | 7 |
| Feb | 40.3 | 52.0 | 19 | 4 | 11 | 9 |
| Mar | 1.5 | 2.3 | 25 | 6 | 24 | 6 |
| Apr | 27.9 | 51.1 | 22 | 3 | 2 | 16 |
| May | 195.1 | 261.5 | 2 | 11 | 0 | 3 |
| Jun | 126.6 | 156.5 | 3 | 13 | 0 | 5 |
| Jul | 142.7 | 140.0 | 3 | 14 | 0 | 11 |
| Aug | 214.4 | 205.9 | 2 | 11 | 1 | 1 |
| Sep | 236.5 | 289.7 | 1 | 6 | 0 | 6 |
| Oct | 86.3 | 137.3 | 12 | 9 | 9 | 5 |
| Nov | 0.2 | 0.1 | 25 | 5 | 29 | 1 |
| Dec | 0.1 | 2.8 | 29 | 2 | 28 | 2 |

#### Rajshahi July Comparison (2022 vs. 2001–2020 POWER Climatology)
- Rajshahi July 2022 IMERG Total: **142.73 mm**
- Rajshahi July 2022 POWER Total: **140.00 mm**
- Rajshahi 2001–2020 POWER July Mean: **285.41 mm**
- **Is Rajshahi July 2022 IMERG below POWER 2001–2020 July mean? TRUE (deficit: 50.0%)**
- **Is Rajshahi July 2022 POWER below POWER 2001–2020 July mean? TRUE (deficit: 50.9%)**

**Key finding:**
Both independent satellite/reanalysis products (IMERG and POWER) agree closely in July 2022 (142.7 mm vs 140.0 mm). July 2022 in Rajshahi was a **real meteorological and agricultural drought** (approx. 50% below climatology). The failure of the check `Mar > Jul and Apr > Jul` is caused by a flawed climatological assumption in the validation suite, not by a bug or product divergence.

---

### Task D4: Code Check (Percentile Rank & Window Alignment)

#### 1. Code of `percentile_rank` (`backend/app/services/risk/indicators.py`)
```python
def percentile_rank(value: float, sorted_sample: Sequence[float]) -> float:
    """Empirical percentile rank (0 to 100) of `value` within an ascending sample.

    Ties use the mid-rank convention: (count_below + 0.5 * count_equal) / n * 100.
    """
    n = len(sorted_sample)
    if n == 0:
        raise ValueError("sorted_sample must not be empty")
    below = bisect_left(sorted_sample, value)
    upto = bisect_right(sorted_sample, value)
    return (below + 0.5 * (upto - below)) / n * 100.0
```

#### 2. Code of `rolling_sum` (`backend/app/services/risk/indicators.py`)
```python
def rolling_sum(series: pd.Series, days: int) -> pd.Series:
    """Trailing sum over `days` observations; NaN until a full window is available."""
    if days < 1:
        raise ValueError("days must be >= 1")
    return series.rolling(window=days, min_periods=days).sum()
```

#### 3. Baseline Rolling Sum Code (`backend/app/services/risk/baseline.py`)
```python
    full = frame.reindex(pd.date_range(frame.index.min(), frame.index.max(), freq="D"))
    rain = full["PRECTOTCORR"]
    rain3 = rolling_sum(rain, 3).to_numpy()
    rain7 = rolling_sum(rain, 7).to_numpy()
    rain30 = rolling_sum(rain, 30).to_numpy()
    tmax = full["T2M_MAX"].to_numpy()
    soil = full["GWETROOT"].to_numpy()
    doy = full.index.dayofyear.to_numpy()
```

#### 4. Live `rain_sums` Code (`pipeline/run_pipeline.py`)
```python
def rain_sums(daily: Mapping[date, float | None], day: date) -> dict[int, float | None]:
    """Rainfall totals (mm) over 3, 7 and 30 days ending at `day`; None if any day is missing."""
    sums: dict[int, float | None] = {}
    for window in (3, 7, RAIN_WINDOW_DAYS):
        values = [daily.get(day - timedelta(days=i)) for i in range(window)]
        sums[window] = None if any(v is None for v in values) else float(sum(values))
    return sums
```

#### 5. Synthetic Test & Window Alignment Verification
- Synthetic test: `percentile_rank(0.0, [0.0]*70 + [10.0]*30)` = **35.0** (mid-rank of 70% tie).
- Non-zero sensitivity: `percentile_rank(0.01, [0.0]*70 + [10.0]*30)` = **70.0** (immediately jumps past all 70 tied zero values).
- End-date alignment: Baseline rolling sums (`pandas.rolling(window, min_periods).sum()`) and live sums (`rain_sums`) both compute a trailing sum of length $N$ ending on `day` (inclusive). Alignment test passed identically (`True`).

---

### Task D5: Offline What-If (Fixed Wet-Day Threshold = 1.0 mm)

Applied a strict wet-day rule fixed in advance: **daily rainfall $< 1.0\text{ mm} \implies 0.0\text{ mm}$**, applied identically to the 2001–2020 POWER baseline and to live 2022 IMERG. No other value was tested.

#### A. Sylhet Monthly High Flood Days Comparison
| Month | Current High Days | What-If (1.0 mm) High Days | Delta |
|---|---|---|---|
| Jan | 21 | 6 | -15 |
| Feb | 11 | 12 | +1 |
| Mar | 0 | 0 | 0 |
| Apr | 11 | 11 | 0 |
| May | 18 | 18 | 0 |
| Jun | 22 | 22 | 0 |
| Jul | 1 | 1 | 0 |
| Aug | 0 | 0 | 0 |
| Sep | 8 | 8 | 0 |
| Oct | 12 | 11 | -1 |
| Nov | 0 | 0 | 0 |
| Dec | 4 | 0 | -4 |

**Sylhet monthly mean flood score in January dropped from 73.35 (High) to 58.60 (Moderate).**

#### B. Sylhet Event Metrics Comparison (2022-05-15 to 2022-09-30)
| Measure | Current Baseline & IMERG | What-If (1.0 mm Threshold) |
|---|---|---|
| Date of first Moderate-or-higher flood level | 2022-05-15 | 2022-05-15 |
| Date of first High flood level | 2022-05-15 | 2022-05-15 |
| Reference onset date | 2022-06-16 | 2022-06-16 |
| Lead time (onset minus first High), days | 32 (target of at least 3 days MET) | 32 (target of at least 3 days MET) |
| High days before the onset | 22 | 22 |
| High days from the onset to 2022-06-30 | 10 | 10 |
| High-level false alarm days (2022-07-01 to 2022-09-30) | 9 | 9 |
| Days scored from 2022-05-15 to 2022-09-30 | 139 | 139 |

*Note:* In May 2022, daily rainfall in Sylhet was heavily above 1.0 mm (mean May 3-day rain was 77.2 mm). The 1.0 mm threshold has zero effect on the May flood event. The lead time of 32 days remains censored by the window start date.

#### C. Seasonality Checks Comparison
| Check | Current Result | Current Detail | What-If Result | What-If Detail |
|---|---|---|---|---|
| Flood score for Sylhet peaks between June and September | PASS | peak month by monthly mean = Jun (78.7) | PASS | peak month by monthly mean = Jun (78.7) |
| Flood score for Sunamganj peaks between June and September | PASS | peak month by monthly mean = Jun (83.5) | PASS | peak month by monthly mean = Jun (83.5) |
| Drought score for Rajshahi is higher in March and April than in July | FAIL | monthly means: Mar 26.1, Apr 64.5, Jul 76.4 | FAIL | monthly means: Mar 26.6, Apr 64.5, Jul 77.0 |
| Salinity score for Satkhira is higher in March to May than in August | PASS | monthly means: Mar 79.4, Apr 92.0, May 52.2, Aug 28.2 | PASS | monthly means: Mar 80.1, Apr 92.1, May 52.3, Aug 28.3 |
| Salinity score for Khulna is higher in March to May than in August | PASS | monthly means: Mar 64.2, Apr 68.9, May 39.0, Aug 17.5 | PASS | monthly means: Mar 64.2, Apr 68.9, May 39.0, Aug 17.6 |
| Salinity score for Rajshahi stays below 20 in every month | PASS | highest daily score in any month = 0.0 (Jan) | PASS | highest daily score in any month = 0.0 (Jan) |

---

## 3. Root Cause Analysis

### 1. Sylhet January False Alarms (R-008)
- **Primary Root Cause:** **Design Limitation (Dry-season Percentile Artifact) + Product Mismatch (Satellite Drizzle Noise)**.
  - The baseline climatology in dry months consists predominantly of zeros (74.6% zeros in January).
  - IMERG microwave/IR retrieval algorithms frequently detect trace precipitation ($< 1.0\text{ mm/day}$) due to atmospheric moisture or cloud reflectance.
  - Due to the mid-rank percentile definition, any trace precipitation (even 0.05 mm over 3 days) exceeds all zeros in the baseline, catapulting the rainfall indicator to the $\ge 75\text{th}$ percentile.
  - Because flood risk assigns a 75% combined weight to 3-day (40%) and 7-day (35%) rainfall percentiles, trace winter drizzle triggers false High alerts.

### 2. Sylhet Lead Time & Pre-Onset High Days (R-008)
- **Primary Root Cause:** **Design Limit / Measurement Censoring (Left-Censored Time Window)**.
  - The backtest window was set to start on `2022-05-15`.
  - In reality, northeastern Bangladesh experienced a massive pre-monsoon flood wave in mid-May 2022. Sylhet was already flooded on 2022-05-15 (score 96.16).
  - Measuring lead time as `REFERENCE_ONSET (2022-06-16) - first_high (2022-05-15) = 32 days` does not measure warning advance time for the June 16 event; it measures the distance to the edge of the arbitrary data window.
  - The 22 High days before June 16 are true alerts for the May event wave, not false alarms for the June event.

### 3. Rajshahi Drought Seasonality Inversion (R-023)
- **Primary Root Cause:** **Real Climate Anomaly + Flawed Validation Rule**.
  - Section 10.4 hardcodes an assumption that drought scores must peak in March/April and stay lower in July.
  - In 2022, northwestern Bangladesh experienced an anomalous and well-documented monsoon drought in July: July rainfall was ~50% below normal across both IMERG (142.7 mm) and POWER (140.0 mm), while root-zone soil wetness fell to the 8.7th percentile.
  - The drought scoring formula operated exactly as designed by flagging this agricultural drought. The validation check failed because it tested a static climatological rule against an anomalous year.

---

## 4. Options Analysis

| Option | Description | Pros | Cons / Feasibility |
|---|---|---|---|
| **A. Wet-Day Threshold (1.0 mm)** *(Recommended)* | Apply a standard meteorological wet-day threshold ($R \ge 1.0\text{ mm/day}$, else 0) identically to POWER baseline computation and live/backtest IMERG. | - Standard meteorological practice (WMO definition of a wet day).<br>- Eliminates 19 winter false High flood days (Jan: 21 $\to$ 6, Dec: 4 $\to$ 0).<br>- Completely offline from existing caches.<br>- Preserves existing architecture. | - Does not eliminate real winter storms (e.g. Jan 11-14 rain of 10.4 mm still triggers alert).<br>- Does not alter July drought score (since July rain was $> 1\text{ mm/day}$). |
| **B. IMERG-Based Baseline** | Download 2001–2020 IMERG daily data to build an IMERG-native climatology instead of NASA POWER. | - Eliminates sensor/retrieval distribution mismatch between POWER and IMERG.<br>- Climatology directly mirrors live satellite retrieval noise. | - **Extremely heavy data volume:** 20 years $\times$ 365.25 days = 7,305 daily global granules to search, download, and clip.<br>- Even a reduced period (2015–2021, 7 years) requires downloading **2,557 NetCDF granules** ($\sim$20–30 GB raw, 1.5–2 hours minimum).<br>- High risk of Earthdata API timeouts or rate limits. |
| **C. Keep As-Is & Document Limitation** | Retain existing code and baselines; update `docs/methodology.md` and user-facing disclaimers to disclose winter dry-season percentile sensitivity and July 2022 drought anomaly. | - Zero risk of introducing regressions.<br>- Zero compute or download overhead. | - System continues to issue false High flood alerts during dry winter drizzle.<br>- Fails validation check in automated testing. |

---

## 5. Recommendation

1. **Adopt Option A (Phase C4):** Introduce `WET_DAY_MM = 1.0` in preprocessing for both POWER baseline generation and live IMERG feeds. This removes 71% of January false High flood days and 100% of December false High flood days with zero network overhead.
2. **Handle Left-Censoring in Frontend & Documentation (Phase C1 / C5):** When `first_high` coincides with the series start date (`2022-05-15`), display that flood risk was already High on the opening day of observation, and state that the lead time is at least 32 days from that window boundary.
3. **Clarify the Rajshahi Drought Check in Documentation (Phase C5):** Retain the drought scoring formula untouched, and document in `docs/methodology.md` that July 2022 was an anomalous drought year with measured 50% precipitation deficits across both IMERG and POWER.
