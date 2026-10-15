"""Unit and integration tests for backtest and event replay (Section 9 task 8.6, 10.1)."""
from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from backend.app.models import District, Observation, RiskSnapshot
from backend.app.services.backtest import (
    REFERENCE_ONSET_DEFAULT,
    compute_backtest,
)


def _make_point(
    dt: str,
    flood_score: float,
    flood_level: str,
    r3_pctl: float | None = None,
    r7_pctl: float | None = None,
    rain_mm: float | None = None,
    soil_wetness: float | None = None,
) -> dict[str, Any]:
    return {
        "date": dt,
        "flood_score": flood_score,
        "flood_level": flood_level,
        "rain3_pctl": r3_pctl,
        "rain7_pctl": r7_pctl,
        "rain_mm": rain_mm,
        "soil_wetness": soil_wetness,
    }


def test_synthetic_series_known_dates():
    """Derived 5 steps on a synthetic series with precisely known milestone dates."""
    series = [
        _make_point("2022-06-01", flood_score=20.0, flood_level="low", r3_pctl=25.0, r7_pctl=20.0),
        _make_point("2022-06-03", flood_score=30.0, flood_level="low", r3_pctl=55.0, r7_pctl=35.0),   # step 1: rain3 > 50
        _make_point("2022-06-05", flood_score=35.0, flood_level="low", r3_pctl=70.0, r7_pctl=65.0),   # step 2: rain7 >= 60
        _make_point("2022-06-08", flood_score=55.0, flood_level="moderate", r3_pctl=80.0, r7_pctl=75.0), # step 3: moderate
        _make_point("2022-06-11", flood_score=82.0, flood_level="high", r3_pctl=95.0, r7_pctl=90.0),     # step 4: high
        _make_point("2022-06-16", flood_score=98.0, flood_level="high", r3_pctl=99.0, r7_pctl=98.0),     # reference onset
    ]

    res = compute_backtest(series, reference_onset="2022-06-16")

    assert res["district_id"] == "sylhet"
    assert res["first_moderate"] == "2022-06-08"
    assert res["first_high"] == "2022-06-11"
    assert res["reference_onset"] == "2022-06-16"
    assert res["lead_time_days"] == 5  # June 16 - June 11 = 5 days

    steps = res["steps"]
    assert len(steps) == 5
    assert steps[0] == {"step": 1, "label": "Rain begins", "label_bn": "বৃষ্টি শুরু", "date": "2022-06-03"}
    assert steps[1] == {"step": 2, "label": "Rain builds", "label_bn": "বৃষ্টি বাড়ছে", "date": "2022-06-05"}
    assert steps[2] == {"step": 3, "label": "Heavy rain", "label_bn": "ভারী বৃষ্টি", "date": "2022-06-08"}
    assert steps[3] == {"step": 4, "label": "Extreme rain", "label_bn": "অতি ভারী বৃষ্টি", "date": "2022-06-11"}
    assert steps[4] == {"step": 5, "label": "Flood", "label_bn": "বন্যা", "date": "2022-06-16"}


def test_series_starting_at_high_or_skipping_moderate():
    """If a series reaches High directly without an exact Moderate day, step 3 accepts Moderate or High."""
    series = [
        _make_point("2022-06-01", flood_score=20.0, flood_level="low", r3_pctl=25.0, r7_pctl=20.0),
        _make_point("2022-06-03", flood_score=30.0, flood_level="low", r3_pctl=55.0, r7_pctl=35.0),
        _make_point("2022-06-05", flood_score=35.0, flood_level="low", r3_pctl=70.0, r7_pctl=65.0),
        _make_point("2022-06-08", flood_score=85.0, flood_level="high", r3_pctl=90.0, r7_pctl=85.0),
        _make_point("2022-06-16", flood_score=98.0, flood_level="high", r3_pctl=99.0, r7_pctl=98.0),
    ]
    res = compute_backtest(series, reference_onset="2022-06-16")
    assert res["first_moderate"] == "2022-06-08"
    assert res["first_high"] == "2022-06-08"
    assert res["lead_time_days"] == 8


def test_lead_time_calculation_variations():
    """Verify lead time calculation responds accurately to varying onset or milestone dates."""
    # 3-day lead time case (matching the spec pitch slide illustrative target)
    series_3d = [
        _make_point("2022-06-05", 25.0, "low", r3_pctl=60.0, r7_pctl=40.0),
        _make_point("2022-06-07", 35.0, "low", r3_pctl=75.0, r7_pctl=65.0),
        _make_point("2022-06-09", 50.0, "moderate", r3_pctl=85.0, r7_pctl=75.0),
        _make_point("2022-06-13", 78.0, "high", r3_pctl=92.0, r7_pctl=85.0),
    ]
    res_3d = compute_backtest(series_3d, reference_onset="2022-06-16")
    assert res_3d["first_high"] == "2022-06-13"
    assert res_3d["lead_time_days"] == 3

    # 7-day lead time case
    series_7d = [
        _make_point("2022-06-02", 30.0, "low", r3_pctl=55.0, r7_pctl=30.0),
        _make_point("2022-06-04", 45.0, "moderate", r3_pctl=70.0, r7_pctl=62.0),
        _make_point("2022-06-09", 75.0, "high", r3_pctl=88.0, r7_pctl=80.0),
    ]
    res_7d = compute_backtest(series_7d, reference_onset="2022-06-16")
    assert res_7d["first_high"] == "2022-06-09"
    assert res_7d["lead_time_days"] == 7


def test_flood_never_reaches_high():
    """If flood never reaches high level, first_high and lead_time_days are None."""
    series = [
        _make_point("2022-06-01", 15.0, "low", r3_pctl=10.0, r7_pctl=10.0),
        _make_point("2022-06-05", 35.0, "low", r3_pctl=55.0, r7_pctl=65.0),
        _make_point("2022-06-10", 55.0, "moderate", r3_pctl=75.0, r7_pctl=70.0),
    ]
    res = compute_backtest(series, reference_onset="2022-06-16")
    assert res["first_moderate"] == "2022-06-10"
    assert res["first_high"] is None
    assert res["lead_time_days"] is None
    assert res["steps"][3]["date"] is None
    assert res["steps"][4]["date"] == "2022-06-16"


def test_empty_series_handled_safely():
    """Empty series does not raise and returns safe null fields."""
    res = compute_backtest([], reference_onset="2022-06-16")
    assert res["district_id"] == "sylhet"
    assert res["series"] == []
    assert res["first_moderate"] is None
    assert res["first_high"] is None
    assert res["lead_time_days"] is None
    assert res["steps"][4]["date"] == "2022-06-16"


def test_public_citation_present():
    """The backtest response includes the public flood onset citation required by Task 8.4."""
    res = compute_backtest([], reference_onset="2022-06-16")
    assert "citation" in res
    assert "Flood Forecasting and Warning Centre" in res["citation"]
    assert "2022" in res["citation"]


@pytest.fixture()
def loaded(session_factory: sessionmaker[Session]) -> sessionmaker[Session]:
    """Seed Sylhet snapshots and observations into the in-memory database."""
    with session_factory() as db:
        for offset, day in enumerate((date(2022, 6, 14), date(2022, 6, 15), date(2022, 6, 16))):
            score = 64.0 + offset * 17.0  # 64, 81, 98
            level = "moderate" if score < 70 else "high"
            db.add(
                RiskSnapshot(
                    district_id="sylhet",
                    date=day,
                    drought_score=5.0,
                    flood_score=score,
                    salt_score=2.0,
                    drought_level="low",
                    flood_level=level,
                    salt_level="low",
                    inputs={
                        "flood": {
                            "score": score,
                            "level": level,
                            "inputs": [
                                {"name": "rain3_pctl", "value": 55.0 + offset * 20.0},
                                {"name": "rain7_pctl", "value": 60.0 + offset * 15.0},
                            ],
                        }
                    },
                    sources={},
                    degraded=False,
                )
            )
            db.add(
                Observation(
                    district_id="sylhet",
                    date=day,
                    source="IMERG_FINAL",
                    variable="precip_mm",
                    value=40.0 + offset * 50.0,
                    product_version="V07",
                )
            )
            db.add(
                Observation(
                    district_id="sylhet",
                    date=day,
                    source="POWER",
                    variable="soil_wetness",
                    value=0.92,
                    product_version="V2",
                )
            )
        db.commit()
    return session_factory


def test_api_backtest_sylhet_endpoint(client: TestClient, loaded: sessionmaker[Session]):
    """Integration test for GET /api/backtest/sylhet-2022."""
    resp = client.get("/api/backtest/sylhet-2022")
    assert resp.status_code == 200
    data = resp.json()

    assert data["district_id"] == "sylhet"
    assert "series" in data
    assert isinstance(data["series"], list)
    assert len(data["series"]) > 0

    first_pt = data["series"][0]
    assert "date" in first_pt
    assert "flood_score" in first_pt
    assert "flood_level" in first_pt

    assert "first_moderate" in data
    assert "first_high" in data
    assert data["reference_onset"] == "2022-06-16"
    assert "lead_time_days" in data
    assert "steps" in data
    assert len(data["steps"]) == 5

    for step in data["steps"]:
        assert set(step.keys()) >= {"step", "label", "date"}
        assert 1 <= step["step"] <= 5


def test_api_backtest_empty_database(client: TestClient):
    """Calling /api/backtest/sylhet-2022 without data returns 404 not_found."""
    resp = client.get("/api/backtest/sylhet-2022")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"
