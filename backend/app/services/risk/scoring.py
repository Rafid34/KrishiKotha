"""Risk scoring engine (Section 7.6).

Computes deterministic flood, drought, and salinity risk scores (0 to 100)
and risk levels ('low', 'moderate', 'high') from NASA Earth observation
indicators and baselines.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Sequence

from .indicators import percentile_rank

# Level thresholds (Section 7.2)
THRESHOLD_MODERATE: float = 40.0
THRESHOLD_HIGH: float = 70.0

# Flood formula weights (Section 7.6)
WEIGHT_FLOOD_RAIN3: float = 0.40
WEIGHT_FLOOD_RAIN7: float = 0.35
WEIGHT_FLOOD_SOIL: float = 0.25

# Drought formula weights and parameters (Section 7.6)
WEIGHT_DROUGHT_SOIL: float = 0.45
WEIGHT_DROUGHT_RAIN: float = 0.35
WEIGHT_DROUGHT_HEAT: float = 0.20
DROUGHT_DEFICIT_SCALE: float = 125.0  # 80% deficit (0.80) scores 100
DROUGHT_HEAT_MAX_ANOMALY: float = 4.0  # +4.0 C anomaly scores 100

# Salinity stress proxy parameters and weights (Section 7.6)
SALT_COAST_MAX_KM: float = 150.0  # 150 km or more scores 0
SALT_COAST_MIN_KM: float = 20.0  # 20 km or less scores 100
SALT_COAST_SPAN_KM: float = 130.0  # 150 - 20 = 130 km

SALT_SEASON_HIGH: float = 100.0  # March to May
SALT_SEASON_MODERATE: float = 60.0  # February and June
SALT_SEASON_LOW: float = 20.0  # other months

# Salinity weights with NDVI (Level 2)
WEIGHT_SALT_SEASON_WITH_NDVI: float = 0.40
WEIGHT_SALT_DRY_WITH_NDVI: float = 0.30
WEIGHT_SALT_VEG_WITH_NDVI: float = 0.30
SALT_NDVI_SCALE: float = 0.10  # -0.10 anomaly scores 100

# Salinity weights without NDVI (Level 1 fallback)
WEIGHT_SALT_SEASON_WITHOUT_NDVI: float = 0.55
WEIGHT_SALT_DRY_WITHOUT_NDVI: float = 0.45

# Named dictionary of all constants echoed by /api/sources (Section 7.6)
SCORING_CONSTANTS: dict[str, Any] = {
    "thresholds": {
        "moderate": THRESHOLD_MODERATE,
        "high": THRESHOLD_HIGH,
    },
    "flood": {
        "weight_rain3": WEIGHT_FLOOD_RAIN3,
        "weight_rain7": WEIGHT_FLOOD_RAIN7,
        "weight_soil": WEIGHT_FLOOD_SOIL,
    },
    "drought": {
        "weight_soil": WEIGHT_DROUGHT_SOIL,
        "weight_rain": WEIGHT_DROUGHT_RAIN,
        "weight_heat": WEIGHT_DROUGHT_HEAT,
        "deficit_scale": DROUGHT_DEFICIT_SCALE,
        "heat_max_anomaly": DROUGHT_HEAT_MAX_ANOMALY,
    },
    "salinity": {
        "coast_max_km": SALT_COAST_MAX_KM,
        "coast_min_km": SALT_COAST_MIN_KM,
        "coast_span_km": SALT_COAST_SPAN_KM,
        "season_scores": {
            "mar_to_may": SALT_SEASON_HIGH,
            "feb_and_jun": SALT_SEASON_MODERATE,
            "other": SALT_SEASON_LOW,
        },
        "weights_with_ndvi": {
            "season": WEIGHT_SALT_SEASON_WITH_NDVI,
            "dry": WEIGHT_SALT_DRY_WITH_NDVI,
            "veg": WEIGHT_SALT_VEG_WITH_NDVI,
        },
        "weights_without_ndvi": {
            "season": WEIGHT_SALT_SEASON_WITHOUT_NDVI,
            "dry": WEIGHT_SALT_DRY_WITHOUT_NDVI,
        },
        "ndvi_scale": SALT_NDVI_SCALE,
    },
}


def clamp(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Clamp numeric value to [min_val, max_val]."""
    if value < min_val:
        return min_val
    if value > max_val:
        return max_val
    return float(value)


def level_for(score: float) -> str:
    """Return risk level ('low', 'moderate', 'high') for a score in [0, 100].

    Level thresholds (Section 7.2):
    - Below 40 is 'low'
    - 40 to 69.99 is 'moderate'
    - 70 and above is 'high'
    """
    if score >= THRESHOLD_HIGH:
        return "high"
    if score >= THRESHOLD_MODERATE:
        return "moderate"
    return "low"


def score_flood(
    rain3_pctl: float | None = None,
    rain7_pctl: float | None = None,
    soil_pctl: float | None = None,
    *,
    f_rain3: float | None = None,
    f_rain7: float | None = None,
    f_soil: float | None = None,
    r3: float | None = None,
    b3: Sequence[float] | None = None,
    r7: float | None = None,
    b7: Sequence[float] | None = None,
    soil_wetness: float | None = None,
    soil_baseline: Sequence[float] | None = None,
    rain7_upstream_pctl: float | None = None,
    r7_upstream: float | None = None,
    b7_upstream: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Compute Flood risk score, level, contributing inputs, and degraded status (Section 7.6).

    Formula:
        f_rain3 = pctl(R3, B3)
        f_rain7 = pctl(R7, B7)
        f_soil  = soil_pctl
        FLOOD   = 0.40*f_rain3 + 0.35*f_rain7 + 0.25*f_soil
    Level 3 extension: f_rain7 uses the larger of local and upstream rainfall percentile.
    If soil_pctl is missing, reweights remaining inputs and sets degraded: true.
    """
    # Resolve aliases
    if rain3_pctl is None and f_rain3 is not None:
        rain3_pctl = f_rain3
    if rain7_pctl is None and f_rain7 is not None:
        rain7_pctl = f_rain7
    if soil_pctl is None and f_soil is not None:
        soil_pctl = f_soil

    # Resolve 3-day rain percentile
    if rain3_pctl is not None:
        sub_rain3 = clamp(float(rain3_pctl), 0.0, 100.0)
        raw_r3 = r3 if r3 is not None else rain3_pctl
    elif r3 is not None and b3 is not None:
        sub_rain3 = percentile_rank(float(r3), b3)
        raw_r3 = r3
    else:
        sub_rain3 = 0.0
        raw_r3 = 0.0

    # Resolve 7-day rain percentile
    if rain7_pctl is not None:
        sub_rain7 = clamp(float(rain7_pctl), 0.0, 100.0)
        raw_r7 = r7 if r7 is not None else rain7_pctl
    elif r7 is not None and b7 is not None:
        sub_rain7 = percentile_rank(float(r7), b7)
        raw_r7 = r7
    else:
        sub_rain7 = 0.0
        raw_r7 = 0.0

    # Level 3 upstream rain extension
    if rain7_upstream_pctl is not None:
        upstream_sub = clamp(float(rain7_upstream_pctl), 0.0, 100.0)
        sub_rain7 = max(sub_rain7, upstream_sub)
    elif r7_upstream is not None and b7_upstream is not None:
        upstream_sub = percentile_rank(float(r7_upstream), b7_upstream)
        sub_rain7 = max(sub_rain7, upstream_sub)

    # Resolve soil wetness percentile
    if soil_pctl is not None:
        sub_soil: float | None = clamp(float(soil_pctl), 0.0, 100.0)
        raw_soil: float | None = soil_wetness if soil_wetness is not None else soil_pctl
    elif soil_wetness is not None and soil_baseline is not None:
        sub_soil = percentile_rank(float(soil_wetness), soil_baseline)
        raw_soil = soil_wetness
    else:
        sub_soil = None
        raw_soil = None

    if sub_soil is not None:
        degraded = False
        score = (
            WEIGHT_FLOOD_RAIN3 * sub_rain3
            + WEIGHT_FLOOD_RAIN7 * sub_rain7
            + WEIGHT_FLOOD_SOIL * sub_soil
        )
        inputs = [
            {
                "name": "rain3_pctl",
                "raw": raw_r3,
                "value": sub_rain3,
                "sub_score": sub_rain3,
                "weight": WEIGHT_FLOOD_RAIN3,
            },
            {
                "name": "rain7_pctl",
                "raw": raw_r7,
                "value": sub_rain7,
                "sub_score": sub_rain7,
                "weight": WEIGHT_FLOOD_RAIN7,
            },
            {
                "name": "soil_pctl",
                "raw": raw_soil,
                "value": sub_soil,
                "sub_score": sub_soil,
                "weight": WEIGHT_FLOOD_SOIL,
            },
        ]
    else:
        # Fallback when soil is missing: reweight rain inputs
        degraded = True
        available_weight = WEIGHT_FLOOD_RAIN3 + WEIGHT_FLOOD_RAIN7
        w_rain3 = WEIGHT_FLOOD_RAIN3 / available_weight
        w_rain7 = WEIGHT_FLOOD_RAIN7 / available_weight
        score = w_rain3 * sub_rain3 + w_rain7 * sub_rain7
        inputs = [
            {
                "name": "rain3_pctl",
                "raw": raw_r3,
                "value": sub_rain3,
                "sub_score": sub_rain3,
                "weight": round(w_rain3, 4),
            },
            {
                "name": "rain7_pctl",
                "raw": raw_r7,
                "value": sub_rain7,
                "sub_score": sub_rain7,
                "weight": round(w_rain7, 4),
            },
            {
                "name": "soil_pctl",
                "raw": None,
                "value": None,
                "sub_score": None,
                "weight": 0.0,
            },
        ]

    clamped_score = clamp(score, 0.0, 100.0)
    rounded_score = round(clamped_score, 2)
    return {
        "score": rounded_score,
        "level": level_for(rounded_score),
        "inputs": inputs,
        "degraded": degraded,
        "soil_missing": sub_soil is None,
    }


def score_drought(
    soil_pctl: float | None = None,
    r30: float | None = None,
    b30_mean: float | None = None,
    tmax7: float | None = None,
    tbase: float | None = None,
    *,
    deficit: float | None = None,
    d_rain: float | None = None,
    d_soil: float | None = None,
    d_heat: float | None = None,
    t_anomaly: float | None = None,
    soil_wetness: float | None = None,
    soil_baseline: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Compute Drought risk score, level, contributing inputs, and degraded status (Section 7.6).

    Formula:
        deficit = max(0, 1 - R30 / B30mean)
        d_rain  = min(100, deficit * 125)          # 80 percent deficit scores 100
        d_soil  = 100 - soil_pctl
        d_heat  = clamp((Tmax7 - Tbase) / 4 * 100, 0, 100)   # +4 C anomaly scores 100
        DROUGHT = 0.45*d_soil + 0.35*d_rain + 0.20*d_heat
    If soil_pctl is missing, reweights remaining inputs and sets degraded: true.
    """
    # 1. Rain deficit
    if d_rain is not None:
        sub_rain = clamp(float(d_rain), 0.0, 100.0)
        raw_deficit = deficit if deficit is not None else (sub_rain / DROUGHT_DEFICIT_SCALE)
    elif deficit is not None:
        raw_deficit = max(0.0, float(deficit))
        sub_rain = min(100.0, raw_deficit * DROUGHT_DEFICIT_SCALE)
    elif r30 is not None and b30_mean is not None:
        if b30_mean > 0:
            raw_deficit = max(0.0, 1.0 - (float(r30) / float(b30_mean)))
        else:
            raw_deficit = 0.0
        sub_rain = min(100.0, raw_deficit * DROUGHT_DEFICIT_SCALE)
    else:
        raw_deficit = 0.0
        sub_rain = 0.0

    # 2. Soil dryness
    if soil_pctl is not None:
        raw_soil: float | None = float(soil_pctl)
        sub_soil: float | None = clamp(100.0 - raw_soil, 0.0, 100.0)
    elif soil_wetness is not None and soil_baseline is not None:
        raw_soil = percentile_rank(float(soil_wetness), soil_baseline)
        sub_soil = clamp(100.0 - raw_soil, 0.0, 100.0)
    elif d_soil is not None:
        sub_soil = clamp(float(d_soil), 0.0, 100.0)
        raw_soil = 100.0 - sub_soil
    else:
        raw_soil = None
        sub_soil = None

    # 3. Heat anomaly
    # heat_missing stays True only when none of the heat inputs are provided (Tmax7 absent).
    heat_missing = False
    sub_heat: float | None
    raw_temp_anom: float | None
    if d_heat is not None:
        sub_heat = clamp(float(d_heat), 0.0, 100.0)
        raw_temp_anom = (sub_heat / 100.0) * DROUGHT_HEAT_MAX_ANOMALY
    elif tmax7 is not None and tbase is not None:
        raw_temp_anom = float(tmax7) - float(tbase)
        sub_heat = clamp((raw_temp_anom / DROUGHT_HEAT_MAX_ANOMALY) * 100.0, 0.0, 100.0)
    elif t_anomaly is not None:
        raw_temp_anom = float(t_anomaly)
        sub_heat = clamp((raw_temp_anom / DROUGHT_HEAT_MAX_ANOMALY) * 100.0, 0.0, 100.0)
    else:
        # Tmax7 unavailable: heat term will be dropped and remaining weights renormalized.
        heat_missing = True
        raw_temp_anom = None
        sub_heat = None

    if sub_soil is not None and sub_heat is not None:
        # All inputs available: full formula (Section 7.6)
        degraded = False
        score = (
            WEIGHT_DROUGHT_SOIL * sub_soil
            + WEIGHT_DROUGHT_RAIN * sub_rain
            + WEIGHT_DROUGHT_HEAT * sub_heat
        )
        inputs = [
            {
                "name": "soil_pctl",
                "raw": raw_soil,
                "value": sub_soil,
                "sub_score": sub_soil,
                "weight": WEIGHT_DROUGHT_SOIL,
            },
            {
                "name": "rain_deficit",
                "raw": raw_deficit,
                "value": sub_rain,
                "sub_score": sub_rain,
                "weight": WEIGHT_DROUGHT_RAIN,
            },
            {
                "name": "heat_anomaly",
                "raw": raw_temp_anom,
                "value": sub_heat,
                "sub_score": sub_heat,
                "weight": WEIGHT_DROUGHT_HEAT,
            },
        ]
    elif sub_soil is None and sub_heat is not None:
        # Soil missing: reweight rain and heat inputs (existing behavior)
        degraded = True
        available_weight = WEIGHT_DROUGHT_RAIN + WEIGHT_DROUGHT_HEAT
        w_rain = WEIGHT_DROUGHT_RAIN / available_weight
        w_heat = WEIGHT_DROUGHT_HEAT / available_weight
        score = w_rain * sub_rain + w_heat * sub_heat
        inputs = [
            {
                "name": "soil_pctl",
                "raw": None,
                "value": None,
                "sub_score": None,
                "weight": 0.0,
            },
            {
                "name": "rain_deficit",
                "raw": raw_deficit,
                "value": sub_rain,
                "sub_score": sub_rain,
                "weight": round(w_rain, 4),
            },
            {
                "name": "heat_anomaly",
                "raw": raw_temp_anom,
                "value": sub_heat,
                "sub_score": sub_heat,
                "weight": round(w_heat, 4),
            },
        ]
    elif sub_soil is not None and sub_heat is None:
        # Tmax7 missing: drop heat term and renormalize soil and rain (Section 7.6)
        degraded = True
        available_weight = WEIGHT_DROUGHT_SOIL + WEIGHT_DROUGHT_RAIN
        w_soil = WEIGHT_DROUGHT_SOIL / available_weight
        w_rain = WEIGHT_DROUGHT_RAIN / available_weight
        score = w_soil * sub_soil + w_rain * sub_rain
        inputs = [
            {
                "name": "soil_pctl",
                "raw": raw_soil,
                "value": sub_soil,
                "sub_score": sub_soil,
                "weight": round(w_soil, 4),
            },
            {
                "name": "rain_deficit",
                "raw": raw_deficit,
                "value": sub_rain,
                "sub_score": sub_rain,
                "weight": round(w_rain, 4),
            },
            {
                "name": "heat_anomaly",
                "raw": None,
                "value": None,
                "sub_score": None,
                "weight": 0.0,
            },
        ]
    else:
        # Both soil and Tmax7 missing: only rain term
        degraded = True
        score = sub_rain
        inputs = [
            {
                "name": "soil_pctl",
                "raw": None,
                "value": None,
                "sub_score": None,
                "weight": 0.0,
            },
            {
                "name": "rain_deficit",
                "raw": raw_deficit,
                "value": sub_rain,
                "sub_score": sub_rain,
                "weight": 1.0,
            },
            {
                "name": "heat_anomaly",
                "raw": None,
                "value": None,
                "sub_score": None,
                "weight": 0.0,
            },
        ]

    clamped_score = clamp(score, 0.0, 100.0)
    rounded_score = round(clamped_score, 2)
    return {
        "score": rounded_score,
        "level": level_for(rounded_score),
        "inputs": inputs,
        "degraded": degraded,
        "tmax_missing": heat_missing,
        "soil_missing": sub_soil is None,
    }


def score_salt(
    coastal_distance_km: float,
    month: int | None = None,
    r30: float | None = None,
    b30_mean: float | None = None,
    *,
    date_val: date | datetime | str | None = None,
    deficit: float | None = None,
    d_rain: float | None = None,
    ndvi_anom: float | None = None,
    degraded: bool | None = None,
) -> dict[str, Any]:
    """Compute Salinity stress proxy score, level, contributing inputs, and degraded status (Section 7.6).

    Formulas:
        s_coast  = clamp((150 - coastal_distance_km) / 130 * 100, 0, 100)
        s_season = 100 for Mar to May; 60 for Feb and Jun; 20 otherwise
        s_dry    = d_rain
        s_veg    = clamp(-ndvi_anom / 0.10 * 100, 0, 100)

        SALT (with NDVI)    = (s_coast / 100) * (0.40*s_season + 0.30*s_dry + 0.30*s_veg)
        SALT (without NDVI) = (s_coast / 100) * (0.55*s_season + 0.45*s_dry) # degraded = false (Level 1)
    """
    raw_dist = float(coastal_distance_km)
    s_coast = clamp((SALT_COAST_MAX_KM - raw_dist) / SALT_COAST_SPAN_KM * 100.0, 0.0, 100.0)

    # Resolve month and season score
    month_num: int | None = None
    if month is not None:
        month_num = int(month)
    elif date_val is not None:
        if isinstance(date_val, (date, datetime)):
            month_num = date_val.month
        elif isinstance(date_val, str):
            month_num = int(date_val.split("-")[1])

    if month_num is not None:
        if month_num in (3, 4, 5):
            s_season = SALT_SEASON_HIGH
        elif month_num in (2, 6):
            s_season = SALT_SEASON_MODERATE
        else:
            s_season = SALT_SEASON_LOW
    else:
        s_season = SALT_SEASON_LOW

    # Resolve rain deficit (s_dry = d_rain)
    if d_rain is not None:
        s_dry = clamp(float(d_rain), 0.0, 100.0)
        raw_deficit = deficit if deficit is not None else (s_dry / DROUGHT_DEFICIT_SCALE)
    elif deficit is not None:
        raw_deficit = max(0.0, float(deficit))
        s_dry = min(100.0, raw_deficit * DROUGHT_DEFICIT_SCALE)
    elif r30 is not None and b30_mean is not None:
        if b30_mean > 0:
            raw_deficit = max(0.0, 1.0 - (float(r30) / float(b30_mean)))
        else:
            raw_deficit = 0.0
        s_dry = min(100.0, raw_deficit * DROUGHT_DEFICIT_SCALE)
    else:
        raw_deficit = 0.0
        s_dry = 0.0

    if ndvi_anom is not None:
        raw_ndvi = float(ndvi_anom)
        s_veg = clamp((-raw_ndvi / SALT_NDVI_SCALE) * 100.0, 0.0, 100.0)
        score = (s_coast / 100.0) * (
            WEIGHT_SALT_SEASON_WITH_NDVI * s_season
            + WEIGHT_SALT_DRY_WITH_NDVI * s_dry
            + WEIGHT_SALT_VEG_WITH_NDVI * s_veg
        )
        is_degraded = False if degraded is None else degraded
        inputs = [
            {
                "name": "coastal_proximity",
                "raw": raw_dist,
                "value": s_coast,
                "sub_score": s_coast,
                "weight": 1.0,
            },
            {
                "name": "seasonal_intrusion",
                "raw": month_num,
                "value": s_season,
                "sub_score": s_season,
                "weight": WEIGHT_SALT_SEASON_WITH_NDVI,
            },
            {
                "name": "rain_deficit",
                "raw": raw_deficit,
                "value": s_dry,
                "sub_score": s_dry,
                "weight": WEIGHT_SALT_DRY_WITH_NDVI,
            },
            {
                "name": "vegetation_anomaly",
                "raw": raw_ndvi,
                "value": s_veg,
                "sub_score": s_veg,
                "weight": WEIGHT_SALT_VEG_WITH_NDVI,
            },
        ]
    else:
        # Documented Level 1 formula without NDVI
        score = (s_coast / 100.0) * (
            WEIGHT_SALT_SEASON_WITHOUT_NDVI * s_season
            + WEIGHT_SALT_DRY_WITHOUT_NDVI * s_dry
        )
        is_degraded = False if degraded is None else degraded
        inputs = [
            {
                "name": "coastal_proximity",
                "raw": raw_dist,
                "value": s_coast,
                "sub_score": s_coast,
                "weight": 1.0,
            },
            {
                "name": "seasonal_intrusion",
                "raw": month_num,
                "value": s_season,
                "sub_score": s_season,
                "weight": WEIGHT_SALT_SEASON_WITHOUT_NDVI,
            },
            {
                "name": "rain_deficit",
                "raw": raw_deficit,
                "value": s_dry,
                "sub_score": s_dry,
                "weight": WEIGHT_SALT_DRY_WITHOUT_NDVI,
            },
        ]

    clamped_score = clamp(score, 0.0, 100.0)
    rounded_score = round(clamped_score, 2)
    return {
        "score": rounded_score,
        "level": level_for(rounded_score),
        "inputs": inputs,
        "degraded": is_degraded,
    }
