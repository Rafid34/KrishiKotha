"""Pure measurement helpers of `pipeline/validate.py` (Section 10.4) on synthetic series."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from pipeline import validate as v


def series(levels: dict[str, str], start: str = "2022-05-15", end: str = "2022-09-30"):
    """Daily `(date, score, level)` rows; dates not in `levels` are low."""
    out = []
    day, last = date.fromisoformat(start), date.fromisoformat(end)
    while day <= last:
        level = levels.get(day.isoformat(), "low")
        out.append((day, {"low": 10.0, "moderate": 50.0, "high": 80.0}[level], level))
        day += timedelta(days=1)
    return out


def test_lead_time_and_false_alarms_on_synthetic_series() -> None:
    levels = {
        "2022-06-05": "moderate",
        "2022-06-10": "moderate",
        "2022-06-11": "high",
        "2022-06-12": "high",
        "2022-06-16": "high",
        "2022-07-04": "high",
        "2022-08-01": "high",
        "2022-08-02": "high",
    }
    m = v.event_metrics(series(levels))
    assert m["first_moderate"] == date(2022, 6, 5)
    assert m["first_high"] == date(2022, 6, 11)
    assert m["lead_time_days"] == 5
    assert len(m["high_days_before_onset"]) == 2
    assert len(m["high_days_onset_to_event_end"]) == 1
    assert m["false_alarm_days"] == 3
    assert m["days_in_window"] == 139


def test_first_moderate_counts_a_direct_jump_to_high() -> None:
    m = v.event_metrics(series({"2022-06-01": "high"}))
    assert m["first_moderate"] == date(2022, 6, 1)
    assert m["first_high"] == date(2022, 6, 1)
    assert m["lead_time_days"] == 15


def test_lead_time_is_negative_when_high_comes_after_onset_and_none_without_high() -> None:
    late = v.event_metrics(series({"2022-06-18": "high"}))
    assert late["lead_time_days"] == -2
    none = v.event_metrics(series({"2022-06-18": "moderate"}))
    assert none["first_high"] is None
    assert none["lead_time_days"] is None


def test_high_days_after_window_end_are_not_counted() -> None:
    m = v.event_metrics(series({"2022-10-05": "high"}, end="2022-10-31"))
    assert m["false_alarm_days"] == 0


def test_pearson_known_values_and_undefined_cases() -> None:
    assert v.pearson([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)
    assert v.pearson([1, 2, 3, 4], [8, 6, 4, 2]) == pytest.approx(-1.0)
    assert v.pearson([1, 1, 1], [1, 2, 3]) is None
    assert v.pearson([1], [1]) is None


def test_compare_rain_ignores_days_missing_in_either_product() -> None:
    d = date(2022, 6, 1)
    imerg = {d: 10.0, d + timedelta(days=1): 20.0, d + timedelta(days=2): None, d + timedelta(days=3): 5.0}
    power = {d: 8.0, d + timedelta(days=1): 25.0, d + timedelta(days=2): 7.0}
    out = v.compare_rain(imerg, power)
    assert out["days"] == 2
    assert out["mean_abs_diff_mm"] == pytest.approx(3.5)
    assert out["mean_diff_mm"] == pytest.approx(-1.5)
    assert out["imerg_total_mm"] == pytest.approx(30.0)
    assert out["power_total_mm"] == pytest.approx(33.0)


def test_compare_rain_with_no_overlap() -> None:
    out = v.compare_rain({}, {})
    assert out["days"] == 0
    assert out["pearson_r"] is None
    assert out["mean_abs_diff_mm"] is None


def test_monthly_stats_and_peak_month() -> None:
    rows = [(date(2022, 1, 1), 10.0), (date(2022, 1, 2), 30.0), (date(2022, 7, 1), 60.0), (date(2022, 7, 2), 50.0)]
    stats = v.monthly_stats(rows)
    assert stats[1] == {"mean": 20.0, "max": 30.0, "days": 2}
    assert stats[7]["mean"] == 55.0
    assert v.peak_month(stats) == 7


def _stats(per_month: dict[int, float]) -> dict[int, dict[str, float]]:
    return {m: {"mean": x, "max": x, "days": 30} for m, x in per_month.items()}


def _months(default: float, **override: float) -> dict[int, float]:
    """Twelve monthly values; keyword `m7=80` overrides July."""
    months = {m: default for m in range(1, 13)}
    months.update({int(k[1:]): val for k, val in override.items()})
    return months


def _profile(**overrides: dict) -> dict:
    base = {
        "sylhet": {"flood": _stats(_months(10.0, m7=80.0))},
        "sunamganj": {"flood": _stats(_months(10.0, m7=80.0))},
        "rajshahi": {
            "drought": _stats(_months(20.0, m3=70.0, m4=60.0)),
            "salt": _stats(_months(0.0)),
        },
        "satkhira": {"salt": _stats(_months(30.0, m3=80.0, m4=80.0, m5=80.0))},
        "khulna": {"salt": _stats(_months(30.0, m3=80.0, m4=80.0, m5=80.0))},
    }
    base.update(overrides)
    return base


def test_seasonality_checks_all_pass_on_a_matching_profile() -> None:
    checks = v.seasonality_checks(_profile())
    assert [c["passed"] for c in checks] == [True] * 6


def test_seasonality_checks_fail_when_the_profile_does_not_match() -> None:
    stats = _profile(
        sunamganj={"flood": _stats(_months(10.0, m2=80.0))},  # peaks in February
        khulna={"salt": _stats(_months(30.0, m3=80.0, m4=80.0, m5=20.0))},  # May below August
    )
    assert [c["passed"] for c in v.seasonality_checks(stats)] == [True, False, True, True, False, True]


def test_rajshahi_salt_check_uses_the_monthly_maximum() -> None:
    stats = _profile(
        rajshahi={
            "drought": _stats(_months(20.0, m3=70.0, m4=60.0)),
            "salt": {1: {"mean": 5.0, "max": 20.0, "days": 31}},
        }
    )
    assert v.seasonality_checks(stats)[-1]["passed"] is False


def test_write_into_replaces_only_the_marked_block(tmp_path) -> None:
    doc = tmp_path / "m.md"
    doc.write_text(f"before\n{v.BEGIN_MARK}\nold\n{v.END_MARK}\nafter\n", encoding="utf-8")
    v.write_into(doc, "new text")
    assert doc.read_text(encoding="utf-8") == f"before\n{v.BEGIN_MARK}\nnew text\n{v.END_MARK}\nafter\n"
    doc.write_text("no markers", encoding="utf-8")
    with pytest.raises(SystemExit):
        v.write_into(doc, "x")
