"""Rolling sums and percentile ranks."""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Sequence

import pandas as pd


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


def rolling_sum(series: pd.Series, days: int) -> pd.Series:
    """Trailing sum over `days` observations; NaN until a full window is available."""
    if days < 1:
        raise ValueError("days must be >= 1")
    return series.rolling(window=days, min_periods=days).sum()
