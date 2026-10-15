"""Route status codes and response shapes, using an in-memory database seeded with fixtures."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from backend.app.models import Observation, PipelineRun, RiskSnapshot


def _inputs(flood: float) -> dict:
    def item(name: str, value: float, weight: float, source: str, data_date: str | None) -> dict:
        return {
            "name": name, "raw": value, "value": value, "sub_score": value,
            "weight": weight, "source": source, "data_date": data_date,
        }

    return {
        "flood": {
            "score": flood, "level": "high",
            "inputs": [
                item("rain3_pctl", 97.0, 0.40, "GPM IMERG Final Run V07", "2022-06-16"),
                item("rain7_pctl", 95.0, 0.35, "GPM IMERG Final Run V07", "2022-06-16"),
                item("soil_pctl", 90.0, 0.25, "NASA POWER GWETROOT", "2022-06-16"),
            ],
        },
        "drought": {"score": 5.0, "level": "low", "inputs": [item("soil_pctl", 10.0, 0.45, "NASA POWER GWETROOT", "2022-06-16")]},
        "salt": {
            "score": 2.0, "level": "low",
            "inputs": [
                item("coastal_proximity", 65.0, 1.0, "Static configuration (non-NASA)", None),
                item("seasonal_intrusion", 100.0, 0.55, "Calendar assumption (non-NASA)", "2022-06-16"),
                item("rain_deficit", 0.0, 0.45, "GPM IMERG Final Run V07", "2022-06-16"),
            ],
        },
    }


def _level(score: float) -> str:
    return "high" if score >= 70 else "moderate" if score >= 40 else "low"


@pytest.fixture()
def loaded(session_factory: sessionmaker[Session]) -> sessionmaker[Session]:
    """Two districts over three days, plus observations and one pipeline run."""
    with session_factory() as db:
        for did, flood in (("sylhet", 84.0), ("rajshahi", 12.0)):
            for offset, day in enumerate((date(2022, 6, 14), date(2022, 6, 15), date(2022, 6, 16))):
                score = flood - (2 - offset) * 10 if did == "sylhet" else flood
                db.add(
                    RiskSnapshot(
                        district_id=did, date=day,
                        drought_score=5.0, flood_score=score, salt_score=2.0,
                        drought_level="low", flood_level=_level(score), salt_level="low",
                        inputs=_inputs(score), sources={}, degraded=(did == "rajshahi"),
                    )
                )
                db.add(Observation(district_id=did, date=day, source="IMERG_FINAL", variable="precip_mm", value=10.0 + offset, product_version="V07"))
                db.add(Observation(district_id=did, date=day, source="POWER", variable="soil_wetness", value=0.9, product_version="V2"))
        db.add(
            PipelineRun(
                started_at=datetime(2026, 10, 14, 1, 0, tzinfo=timezone.utc),
                finished_at=datetime(2026, 10, 14, 1, 5, tzinfo=timezone.utc),
                status="ok", detail={"run": "final"},
            )
        )
        db.commit()
    return session_factory


def test_health(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body == {"status": "ok", "data_mode": "live", "version": "1.0.0"}


def test_districts_and_crops(client: TestClient) -> None:
    districts = client.get("/api/districts").json()
    assert len(districts) == 8
    sylhet = next(d for d in districts if d["id"] == "sylhet")
    assert set(sylhet) == {"id", "name_en", "name_bn", "lat", "lon", "division"}
    assert sylhet["name_bn"] == "সিলেট"
    crops = client.get("/api/crops").json()
    assert {c["id"] for c in crops} == {"aman", "boro", "aus"}
    assert set(crops[0]) == {"id", "name_en", "name_bn"}


def test_risk_map_default_latest_and_date(client: TestClient, loaded: sessionmaker[Session]) -> None:
    body = client.get("/api/risk").json()
    assert body["date"] == "2022-06-16"
    assert [d["district_id"] for d in body["districts"]] == ["rajshahi", "sylhet"]
    sylhet = body["districts"][1]
    assert sylhet["flood"] == {"score": 84.0, "level": "high"}
    assert sylhet["drought"]["level"] == "low" and sylhet["salt"]["score"] == 2.0
    assert sylhet["degraded"] is False and body["districts"][0]["degraded"] is True

    earlier = client.get("/api/risk", params={"date": "2022-06-14"}).json()
    assert earlier["districts"][1]["flood"]["score"] == 64.0


def test_risk_map_hazard_filter(client: TestClient, loaded: sessionmaker[Session]) -> None:
    body = client.get("/api/risk", params={"hazard": "flood"}).json()
    row = body["districts"][1]
    assert set(row) == {"district_id", "flood", "degraded"}


def test_risk_map_errors(client: TestClient, loaded: sessionmaker[Session]) -> None:
    missing = client.get("/api/risk", params={"date": "2020-01-01"})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"
    bad_hazard = client.get("/api/risk", params={"hazard": "fire"})
    assert bad_hazard.status_code == 422
    assert bad_hazard.json()["error"]["code"] == "validation_error"
    assert client.get("/api/risk", params={"date": "yesterday"}).status_code == 422


def test_risk_map_empty_database(client: TestClient) -> None:
    resp = client.get("/api/risk")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_risk_series(client: TestClient, loaded: sessionmaker[Session]) -> None:
    body = client.get("/api/risk/sylhet").json()
    assert body["district_id"] == "sylhet"
    assert [p["date"] for p in body["series"]] == ["2022-06-14", "2022-06-15", "2022-06-16"]
    first = body["series"][0]
    assert set(first) == {"date", "drought_score", "flood_score", "salt_score", "rain_mm", "soil_wetness"}
    assert first["flood_score"] == 64.0 and first["rain_mm"] == 10.0 and first["soil_wetness"] == 0.9

    short = client.get("/api/risk/sylhet", params={"days": 2}).json()["series"]
    assert [p["date"] for p in short] == ["2022-06-15", "2022-06-16"]


def test_risk_series_date_param(client: TestClient, loaded: sessionmaker[Session]) -> None:
    """date= anchors the window end; data after that date is excluded."""
    # Fixture has June 14, 15, 16 for sylhet.  Request window ending at June 15.
    body = client.get("/api/risk/sylhet", params={"date": "2022-06-15"}).json()
    assert body["district_id"] == "sylhet"
    dates = [p["date"] for p in body["series"]]
    assert dates[-1] == "2022-06-15"      # window ends at the requested date
    assert "2022-06-16" not in dates      # latest snapshot is excluded
    assert "2022-06-14" in dates          # earlier data in the window is included

    # days=2 + date=2022-06-15: window is exactly 2022-06-14 to 2022-06-15
    two_day = client.get("/api/risk/sylhet", params={"date": "2022-06-15", "days": 2}).json()["series"]
    assert [p["date"] for p in two_day] == ["2022-06-14", "2022-06-15"]

    # days=1 + date=2022-06-14: window is exactly one day
    one_day = client.get("/api/risk/sylhet", params={"date": "2022-06-14", "days": 1}).json()["series"]
    assert [p["date"] for p in one_day] == ["2022-06-14"]
    assert one_day[0]["flood_score"] == 64.0  # matches fixture: flood=84-20


def test_risk_series_limits_and_unknown_district(client: TestClient, loaded: sessionmaker[Session]) -> None:
    assert client.get("/api/risk/sylhet", params={"days": 365}).status_code == 200
    assert client.get("/api/risk/sylhet", params={"days": 366}).status_code == 422
    assert client.get("/api/risk/sylhet", params={"days": 0}).status_code == 422
    resp = client.get("/api/risk/xyz")
    assert resp.status_code == 404
    assert resp.json() == {"error": {"code": "not_found", "message": "District 'xyz' does not exist"}}
    assert client.get("/api/risk/khulna").json() == {"district_id": "khulna", "series": []}


def test_risk_explain(client: TestClient, loaded: sessionmaker[Session]) -> None:
    body = client.get("/api/risk/sylhet/explain", params={"date": "2022-06-16"}).json()
    assert body["district_id"] == "sylhet" and body["date"] == "2022-06-16"
    assert body["degraded"] is False
    flood = body["flood"]
    assert flood["score"] == 84.0
    first = flood["inputs"][0]
    assert first["name"] == "rain3_pctl" and first["weight"] == 0.40
    assert first["source"] == "GPM IMERG Final Run V07" and first["data_date"] == "2022-06-16"
    assert abs(sum(i["weight"] for i in flood["inputs"]) - 1.0) < 1e-9
    assert body["drought"]["inputs"] and body["salt"]["inputs"]
    assert flood["coastal_factor"] is None


def test_salt_explain_separates_coastal_factor(client: TestClient, loaded: sessionmaker[Session]) -> None:
    salt = client.get("/api/risk/sylhet/explain", params={"date": "2022-06-16"}).json()["salt"]
    assert [i["name"] for i in salt["inputs"]] == ["seasonal_intrusion", "rain_deficit"]
    assert abs(sum(i["weight"] for i in salt["inputs"]) - 1.0) < 1e-9
    factor = salt["coastal_factor"]
    assert factor["name"] == "coastal_proximity" and factor["raw"] == 65.0
    assert factor["value"] == 65.0 and factor["multiplier"] == 0.65
    assert "weight" not in factor
    assert salt["score"] == 2.0  # stored score is untouched

    default = client.get("/api/risk/sylhet/explain").json()
    assert default["date"] == "2022-06-16"


def test_risk_explain_errors(client: TestClient, loaded: sessionmaker[Session]) -> None:
    assert client.get("/api/risk/xyz/explain").status_code == 404
    resp = client.get("/api/risk/sylhet/explain", params={"date": "2021-01-01"})
    assert resp.status_code == 404 and resp.json()["error"]["code"] == "not_found"


def test_sources_shape_and_last_dates(client: TestClient, loaded: sessionmaker[Session]) -> None:
    sources = client.get("/api/sources").json()
    keys = {"name", "short_name", "version", "resolution", "latency", "last_data_date", "url"}
    assert all(set(s) == keys for s in sources)
    by_name = {s["short_name"]: s for s in sources}
    assert by_name["GPM_3IMERGDF"]["last_data_date"] == "2022-06-16"
    assert by_name["GPM_3IMERGDL"]["last_data_date"] is None
    assert by_name["POWER_DAILY"]["last_data_date"] == "2022-06-16"


def test_pipeline_status(client: TestClient, loaded: sessionmaker[Session]) -> None:
    body = client.get("/api/pipeline/status").json()
    assert body["status"] == "ok" and body["detail"] == {"run": "final"}
    assert body["started_at"] == "2026-10-14T01:00:00Z" and body["finished_at"] == "2026-10-14T01:05:00Z"


def test_pipeline_status_none_recorded(client: TestClient) -> None:
    resp = client.get("/api/pipeline/status")
    assert resp.status_code == 404 and resp.json()["error"]["code"] == "not_found"


def test_unknown_route_uses_error_format(client: TestClient) -> None:
    resp = client.get("/api/nope")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_advice_endpoint(client: TestClient, loaded: sessionmaker[Session]) -> None:
    # 1. Success for Sylhet Aman on 2022-06-16
    resp = client.post(
        "/api/advice",
        json={"district_id": "sylhet", "crop_id": "aman", "date": "2022-06-16"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rule_id"] == "flood_high_early"
    assert data["hazard"] == "flood"
    assert data["level"] == "high"
    assert "বন্যার ঝুঁকি বেশি" in data["text_bn"]
    assert "Flood risk is high" in data["text_en"]
    assert data["audio_url"] is None

    # 2. Unknown district -> 404
    resp_dist = client.post(
        "/api/advice",
        json={"district_id": "nowhere", "crop_id": "aman"},
    )
    assert resp_dist.status_code == 404
    assert resp_dist.json()["error"]["code"] == "not_found"

    # 3. Unknown crop -> 404
    resp_crop = client.post(
        "/api/advice",
        json={"district_id": "sylhet", "crop_id": "wheat"},
    )
    assert resp_crop.status_code == 404
    assert resp_crop.json()["error"]["code"] == "not_found"


def test_sim_sms_roundtrip(client: TestClient, loaded: sessionmaker[Session]) -> None:
    """Simulator round trip: POST /api/sim/sms with SYLHET AMAN creates subscriber, two replies, two message_logs."""
    resp = client.post(
        "/api/sim/sms",
        json={"from": "+8801700000000", "body": "SYLHET AMAN"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["replies"]) == 2
    assert "স্বাগতম" in data["replies"][0]["text"]
    assert "বন্যার ঝুঁকি বেশি" in data["replies"][1]["text"]
    sub_id = data["subscriber_id"]
    assert sub_id is not None

    with loaded() as db:
        from backend.app.models import MessageLog, Subscriber

        # Verify subscriber created
        sub = db.get(Subscriber, sub_id)
        assert sub is not None
        assert sub.phone_e164 == "+8801700000000"
        assert sub.district_id == "sylhet"
        assert sub.crop_id == "aman"
        assert sub.active is True

        # Verify exactly two message_logs rows created
        logs = db.query(MessageLog).filter_by(subscriber_id=sub_id).all()
        assert len(logs) == 2
        assert logs[0].rule_id == "welcome"
        assert logs[0].direction == "out"
        assert logs[0].channel == "sim"
        assert logs[1].rule_id == "flood_high_early"
        assert logs[1].direction == "out"
        assert logs[1].channel == "sim"

    # Test STOP command deactivates subscriber
    resp_stop = client.post(
        "/api/sim/sms",
        json={"from": "+8801700000000", "body": "STOP"},
    )
    assert resp_stop.status_code == 200
    stop_data = resp_stop.json()
    assert len(stop_data["replies"]) == 1
    assert "বন্ধ হয়েছে" in stop_data["replies"][0]["text"]

    with loaded() as db:
        from backend.app.models import Subscriber
        sub = db.get(Subscriber, sub_id)
        assert sub.active is False

    # Test HELP command
    resp_help = client.post(
        "/api/sim/sms",
        json={"from": "+8801700000000", "body": "HELP"},
    )
    assert resp_help.status_code == 200
    help_data = resp_help.json()
    assert len(help_data["replies"]) == 1
    assert "SYLHET AMAN" in help_data["replies"][0]["text"]

    # Test with explicit date parameter
    resp_date = client.post(
        "/api/sim/sms",
        json={"from": "+8801700000001", "body": "SYLHET AMAN", "date": "2022-06-16"},
    )
    assert resp_date.status_code == 200
    date_data = resp_date.json()
    assert len(date_data["replies"]) == 2
    assert "স্বাগতম" in date_data["replies"][0]["text"]
    assert "বন্যার ঝুঁকি বেশি" in date_data["replies"][1]["text"]


