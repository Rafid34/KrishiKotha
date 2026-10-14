"""Tests for risk scoring engine (Section 7.6 and Phase 4)."""
from datetime import date
import pytest

from backend.app.services.risk.scoring import (
    DROUGHT_DEFICIT_SCALE,
    DROUGHT_HEAT_MAX_ANOMALY,
    SALT_COAST_MAX_KM,
    SALT_COAST_MIN_KM,
    SALT_COAST_SPAN_KM,
    SALT_NDVI_SCALE,
    SALT_SEASON_HIGH,
    SALT_SEASON_LOW,
    SALT_SEASON_MODERATE,
    SCORING_CONSTANTS,
    THRESHOLD_HIGH,
    THRESHOLD_MODERATE,
    WEIGHT_DROUGHT_HEAT,
    WEIGHT_DROUGHT_RAIN,
    WEIGHT_DROUGHT_SOIL,
    WEIGHT_FLOOD_RAIN3,
    WEIGHT_FLOOD_RAIN7,
    WEIGHT_FLOOD_SOIL,
    WEIGHT_SALT_DRY_WITH_NDVI,
    WEIGHT_SALT_DRY_WITHOUT_NDVI,
    WEIGHT_SALT_SEASON_WITH_NDVI,
    WEIGHT_SALT_SEASON_WITHOUT_NDVI,
    WEIGHT_SALT_VEG_WITH_NDVI,
    clamp,
    level_for,
    score_drought,
    score_flood,
    score_salt,
)


def test_level_for_thresholds():
    """Verify level classification matches Section 7.2 (<40 low, 40-69.99 moderate, >=70 high)."""
    assert level_for(0.0) == "low"
    assert level_for(39.99) == "low"
    assert level_for(40.0) == "moderate"
    assert level_for(55.0) == "moderate"
    assert level_for(69.99) == "moderate"
    assert level_for(70.0) == "high"
    assert level_for(100.0) == "high"


def test_clamp_utility():
    """Verify clamp restricts values to [min_val, max_val]."""
    assert clamp(-15.0) == 0.0
    assert clamp(150.0) == 100.0
    assert clamp(55.5) == 55.5
    assert clamp(5.0, 10.0, 20.0) == 10.0
    assert clamp(25.0, 10.0, 20.0) == 20.0


def test_scoring_weights_and_constants():
    """Verify that all weights and thresholds are declared and sum to 1.0."""
    assert round(WEIGHT_FLOOD_RAIN3 + WEIGHT_FLOOD_RAIN7 + WEIGHT_FLOOD_SOIL, 2) == 1.00
    assert round(WEIGHT_DROUGHT_SOIL + WEIGHT_DROUGHT_RAIN + WEIGHT_DROUGHT_HEAT, 2) == 1.00
    assert round(WEIGHT_SALT_SEASON_WITHOUT_NDVI + WEIGHT_SALT_DRY_WITHOUT_NDVI, 2) == 1.00
    assert round(
        WEIGHT_SALT_SEASON_WITH_NDVI + WEIGHT_SALT_DRY_WITH_NDVI + WEIGHT_SALT_VEG_WITH_NDVI, 2
    ) == 1.00
    assert THRESHOLD_MODERATE == 40.0
    assert THRESHOLD_HIGH == 70.0
    assert "thresholds" in SCORING_CONSTANTS
    assert "flood" in SCORING_CONSTANTS
    assert "drought" in SCORING_CONSTANTS
    assert "salinity" in SCORING_CONSTANTS


def test_flood_extreme_rain_gives_flood_at_least_80():
    """Phase 4 fixture: extreme rain gives flood at least 80."""
    res = score_flood(rain3_pctl=95.0, rain7_pctl=90.0, soil_pctl=70.0)
    # 0.40 * 95 + 0.35 * 90 + 0.25 * 70 = 38.0 + 31.5 + 17.5 = 87.0
    assert res["score"] >= 80.0
    assert res["score"] == 87.0
    assert res["level"] == "high"
    assert res["degraded"] is False
    assert len(res["inputs"]) == 3
    names = [inp["name"] for inp in res["inputs"]]
    assert names == ["rain3_pctl", "rain7_pctl", "soil_pctl"]


def test_flood_with_raw_sample_arrays():
    """Verify raw baseline sample arrays calculate percentile ranks correctly."""
    sample = [10.0, 20.0, 30.0, 40.0]
    res = score_flood(r3=45.0, b3=sample, r7=45.0, b7=sample, soil_wetness=0.9, soil_baseline=[0.2, 0.4])
    assert res["score"] == 100.0
    assert res["level"] == "high"
    assert res["degraded"] is False


def test_flood_upstream_rainfall_extension():
    """Level 3 extension: f_rain7 uses the larger of local and upstream rainfall percentile."""
    res_local = score_flood(rain3_pctl=50.0, rain7_pctl=30.0, soil_pctl=50.0)
    res_upstream = score_flood(
        rain3_pctl=50.0, rain7_pctl=30.0, soil_pctl=50.0, rain7_upstream_pctl=90.0
    )
    # Local only: 0.40*50 + 0.35*30 + 0.25*50 = 20 + 10.5 + 12.5 = 43.0
    assert res_local["score"] == 43.0
    # Upstream: f_rain7 becomes 90 -> 20 + 0.35*90 + 12.5 = 20 + 31.5 + 12.5 = 64.0
    assert res_upstream["score"] == 64.0
    assert res_upstream["score"] > res_local["score"]


def test_flood_missing_soil_sets_degraded():
    """Phase 4 fixture: missing soil input sets degraded: true."""
    res = score_flood(rain3_pctl=80.0, rain7_pctl=80.0, soil_pctl=None)
    assert res["degraded"] is True
    # Reweighted: 0.40/0.75 * 80 + 0.35/0.75 * 80 = 80.0
    assert res["score"] == 80.0
    assert res["level"] == "high"
    soil_input = next(inp for inp in res["inputs"] if inp["name"] == "soil_pctl")
    assert soil_input["value"] is None
    assert soil_input["weight"] == 0.0


def test_drought_dry_soil_and_rain_deficit_gives_at_least_70():
    """Phase 4 fixture: dry soil and rain deficit give drought at least 70."""
    # soil_pctl=10 -> d_soil = 90
    # deficit=0.80 -> d_rain = min(100, 0.8 * 125) = 100
    # tmax7=30, tbase=30 -> d_heat = 0
    # 0.45 * 90 + 0.35 * 100 + 0.20 * 0 = 40.5 + 35.0 + 0 = 75.5 >= 70
    res = score_drought(soil_pctl=10.0, deficit=0.80, tmax7=30.0, tbase=30.0)
    assert res["score"] >= 70.0
    assert res["score"] == 75.5
    assert res["level"] == "high"
    assert res["degraded"] is False
    assert len(res["inputs"]) == 3


def test_drought_heat_anomaly_and_clamping():
    """Test temperature anomaly clamping and excess rainfall handling."""
    # +6 C anomaly clamps d_heat to 100
    res_hot = score_drought(soil_pctl=50.0, deficit=0.0, tmax7=36.0, tbase=30.0)
    # d_soil = 50, d_rain = 0, d_heat = 100
    # 0.45*50 + 0.35*0 + 0.20*100 = 22.5 + 20.0 = 42.5
    assert res_hot["score"] == 42.5
    assert res_hot["level"] == "moderate"

    # Excess rain: R30 > B30mean -> deficit is 0
    res_wet = score_drought(soil_pctl=90.0, r30=200.0, b30_mean=100.0, tmax7=28.0, tbase=30.0)
    # d_soil = 10, d_rain = 0, d_heat = 0
    # 0.45*10 = 4.5
    assert res_wet["score"] == 4.5
    assert res_wet["level"] == "low"


def test_drought_missing_soil_sets_degraded():
    """Phase 4 fixture: missing soil input sets degraded: true for drought."""
    res = score_drought(soil_pctl=None, deficit=0.80, tmax7=32.0, tbase=30.0)
    assert res["degraded"] is True
    # d_rain = 100, d_heat = (2/4)*100 = 50
    # Reweighted over 0.35 + 0.20 = 0.55:
    # (0.35 * 100 + 0.20 * 50) / 0.55 = (35 + 10) / 0.55 = 45 / 0.55 = 81.82
    assert res["score"] == 81.82
    assert res["level"] == "high"
    soil_input = next(inp for inp in res["inputs"] if inp["name"] == "soil_pctl")
    assert soil_input["value"] is None
    assert soil_input["weight"] == 0.0


def test_salt_inland_district_gives_zero():
    """Phase 4 fixture: inland district (coastal distance 350 km) gives salt 0."""
    res = score_salt(coastal_distance_km=350.0, month=4, deficit=0.70)
    assert res["score"] == 0.0
    assert res["level"] == "low"
    assert res["degraded"] is False

    # Coast distance >= 150 km also gives 0
    res_150 = score_salt(coastal_distance_km=150.0, month=4, deficit=1.0)
    assert res_150["score"] == 0.0


def test_salt_coastal_district_in_april_gives_at_least_70():
    """Phase 4 fixture: coastal district in April with 70 percent rain deficit gives salt at least 70."""
    # coastal_distance_km = 20 -> s_coast = 100.0
    # month = 4 (April) -> s_season = 100.0
    # deficit = 0.70 -> d_rain = 0.70 * 125 = 87.5
    # Without NDVI: (100/100) * (0.55 * 100 + 0.45 * 87.5) = 55.0 + 39.375 = 94.38 >= 70
    res = score_salt(coastal_distance_km=20.0, month=4, deficit=0.70)
    assert res["score"] >= 70.0
    assert res["score"] == 94.38
    assert res["level"] == "high"
    assert res["degraded"] is False
    assert len(res["inputs"]) == 3


def test_salt_seasonality_and_date_handling():
    """Verify s_season assignment across calendar months and date formats."""
    # Mar to May: 100
    assert score_salt(coastal_distance_km=20.0, month=3, deficit=0.0)["score"] == 55.0
    assert score_salt(coastal_distance_km=20.0, month=5, deficit=0.0)["score"] == 55.0

    # Feb and Jun: 60 -> (100/100) * (0.55 * 60) = 33.0
    assert score_salt(coastal_distance_km=20.0, month=2, deficit=0.0)["score"] == 33.0
    assert score_salt(coastal_distance_km=20.0, month=6, deficit=0.0)["score"] == 33.0

    # Other months: 20 -> (100/100) * (0.55 * 20) = 11.0
    assert score_salt(coastal_distance_km=20.0, month=8, deficit=0.0)["score"] == 11.0

    # Date object and string handling
    res_date = score_salt(coastal_distance_km=20.0, date_val=date(2022, 4, 15), deficit=0.0)
    assert res_date["score"] == 55.0
    res_str = score_salt(coastal_distance_km=20.0, date_val="2022-04-15", deficit=0.0)
    assert res_str["score"] == 55.0


def test_salt_with_ndvi_level_2():
    """Verify Salinity calculation when NDVI anomaly is available (Level 2)."""
    # s_coast = 100 (20 km), s_season = 100 (April), deficit = 0 (s_dry = 0)
    # ndvi_anom = -0.10 -> s_veg = min(100, -(-0.10)/0.10 * 100) = 100
    # SALT = 1.0 * (0.40 * 100 + 0.30 * 0 + 0.30 * 100) = 40 + 30 = 70.0
    res = score_salt(coastal_distance_km=20.0, month=4, deficit=0.0, ndvi_anom=-0.10)
    assert res["score"] == 70.0
    assert res["level"] == "high"
    assert res["degraded"] is False
    assert len(res["inputs"]) == 4
    veg_input = next(inp for inp in res["inputs"] if inp["name"] == "vegetation_anomaly")
    assert veg_input["value"] == 100.0


def test_drought_missing_tmax_drops_heat_term_and_renormalizes():
    """Section 7.6: missing Tmax7 drops heat term and renormalizes remaining drought weights to 1.0."""
    # soil_pctl=10 -> d_soil=90; deficit=0.80 -> d_rain=100; tmax7 absent
    res = score_drought(soil_pctl=10.0, deficit=0.80)  # no tmax7/tbase
    assert res["degraded"] is True
    assert res["tmax_missing"] is True
    assert res["soil_missing"] is False

    # Renormalized weights: w_soil=0.45/0.80, w_rain=0.35/0.80
    w_soil = WEIGHT_DROUGHT_SOIL / (WEIGHT_DROUGHT_SOIL + WEIGHT_DROUGHT_RAIN)
    w_rain = WEIGHT_DROUGHT_RAIN / (WEIGHT_DROUGHT_SOIL + WEIGHT_DROUGHT_RAIN)
    expected = round(clamp(w_soil * 90.0 + w_rain * 100.0, 0.0, 100.0), 2)
    assert res["score"] == expected  # 0.5625*90 + 0.4375*100 = 50.625 + 43.75 = 94.38

    # Heat entry is dropped (weight 0, value None)
    heat_inp = next(i for i in res["inputs"] if i["name"] == "heat_anomaly")
    assert heat_inp["value"] is None
    assert heat_inp["weight"] == 0.0

    # Active weights sum to 1.0
    total_weight = sum(i["weight"] for i in res["inputs"])
    assert round(total_weight, 10) == 1.0


def test_drought_missing_tmax_score_exceeds_zero_heat_method():
    """New renormalized score is higher than the previous method (zeroed sub_heat, full 0.20 weight)."""
    # soil_pctl=10, deficit=0.80: old method -> 0.45*90 + 0.35*100 + 0.20*0 = 75.5
    res = score_drought(soil_pctl=10.0, deficit=0.80)
    old_method_score = round(
        WEIGHT_DROUGHT_SOIL * 90.0 + WEIGHT_DROUGHT_RAIN * 100.0 + WEIGHT_DROUGHT_HEAT * 0.0, 2
    )
    assert res["score"] > old_method_score  # 94.38 > 75.5


def test_drought_missing_tmax_sets_degraded_and_flag():
    """Section 7.6: missing Tmax7 sets degraded: true and tmax_missing: true."""
    res = score_drought(soil_pctl=50.0, deficit=0.5)  # no tmax7
    assert res["degraded"] is True
    assert res["tmax_missing"] is True

    # Full inputs: no flags set
    full = score_drought(soil_pctl=50.0, deficit=0.5, tmax7=30.0, tbase=30.0)
    assert full["degraded"] is False
    assert full["tmax_missing"] is False
    assert full["soil_missing"] is False


def test_soil_missing_flag_for_flood_and_drought():
    """Section 7.6: missing soil sets soil_missing for both flood and drought."""
    # Flood: soil absent
    flood_miss = score_flood(rain3_pctl=50.0, rain7_pctl=50.0)  # no soil_pctl
    assert flood_miss["soil_missing"] is True
    assert flood_miss["degraded"] is True

    # Flood: soil present
    flood_ok = score_flood(rain3_pctl=50.0, rain7_pctl=50.0, soil_pctl=50.0)
    assert flood_ok["soil_missing"] is False
    assert flood_ok["degraded"] is False

    # Drought: soil absent (heat present)
    drought_miss = score_drought(deficit=0.5, tmax7=30.0, tbase=28.0)  # no soil
    assert drought_miss["soil_missing"] is True
    assert drought_miss["degraded"] is True

    # Drought: soil present
    drought_ok = score_drought(soil_pctl=50.0, deficit=0.5, tmax7=30.0, tbase=28.0)
    assert drought_ok["soil_missing"] is False


def test_drought_both_soil_and_tmax_missing():
    """When both soil and Tmax7 are absent only the rain term is used with weight 1.0."""
    res = score_drought(deficit=0.80)  # no soil, no tmax7
    assert res["degraded"] is True
    assert res["tmax_missing"] is True
    assert res["soil_missing"] is True
    # Only rain: d_rain = min(100, 0.80 * 125) = 100
    assert res["score"] == 100.0
    rain_inp = next(i for i in res["inputs"] if i["name"] == "rain_deficit")
    assert rain_inp["weight"] == 1.0
    total_weight = sum(i["weight"] for i in res["inputs"])
    assert round(total_weight, 10) == 1.0


def test_scoring_determinism():
    """Verify that scoring functions produce identical outputs for identical inputs."""
    flood_1 = score_flood(rain3_pctl=65.2, rain7_pctl=71.8, soil_pctl=45.0)
    flood_2 = score_flood(rain3_pctl=65.2, rain7_pctl=71.8, soil_pctl=45.0)
    assert flood_1 == flood_2

    drought_1 = score_drought(soil_pctl=30.0, deficit=0.45, tmax7=33.5, tbase=31.0)
    drought_2 = score_drought(soil_pctl=30.0, deficit=0.45, tmax7=33.5, tbase=31.0)
    assert drought_1 == drought_2

    salt_1 = score_salt(coastal_distance_km=45.0, month=4, deficit=0.55)
    salt_2 = score_salt(coastal_distance_km=45.0, month=4, deficit=0.55)
    assert salt_1 == salt_2
