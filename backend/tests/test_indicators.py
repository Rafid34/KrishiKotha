"""Rolling sums and percentile ranks."""
import math

import numpy as np
import pandas as pd
import pytest

from backend.app.services.risk.baseline import compute_baseline
from backend.app.services.risk.indicators import percentile_rank, rolling_sum


def test_percentile_rank_basic():
    sample = [1, 2, 3, 4]
    assert percentile_rank(0, sample) == 0.0
    assert percentile_rank(5, sample) == 100.0
    assert percentile_rank(2.5, sample) == 50.0


def test_percentile_rank_ties_use_midrank():
    assert percentile_rank(0, [0, 0, 0, 0]) == 50.0
    assert percentile_rank(1, [0, 1, 1, 2]) == 50.0


def test_percentile_rank_empty_raises():
    with pytest.raises(ValueError):
        percentile_rank(1, [])


def test_rolling_sum_window_and_nan_edges():
    out = rolling_sum(pd.Series([1.0, 2.0, 3.0, 4.0]), 3)
    assert math.isnan(out.iloc[0]) and math.isnan(out.iloc[1])
    assert out.iloc[2] == 6.0 and out.iloc[3] == 9.0


def test_rolling_sum_propagates_missing():
    out = rolling_sum(pd.Series([1.0, np.nan, 3.0, 4.0, 5.0]), 3)
    assert math.isnan(out.iloc[2]) and math.isnan(out.iloc[3])
    assert out.iloc[4] == 12.0


def test_rolling_sum_invalid_days():
    with pytest.raises(ValueError):
        rolling_sum(pd.Series([1.0]), 0)


def test_compute_baseline_constant_series():
    idx = pd.date_range("2001-01-01", "2005-12-31", freq="D")
    frame = pd.DataFrame({"PRECTOTCORR": 2.0, "T2M_MAX": 30.0, "RH2M": 80.0, "GWETROOT": 0.5}, index=idx)
    rows = compute_baseline(frame)
    assert len(rows) == 366
    mid = rows[166]
    assert set(mid["rain3_sorted"]) == {6.0}
    assert set(mid["rain7_sorted"]) == {14.0}
    assert mid["rain30_mean"] == 60.0
    assert mid["tmax_mean"] == 30.0
    assert set(mid["soil_sorted"]) == {0.5}
    assert mid["rain3_sorted"] == sorted(mid["rain3_sorted"])
