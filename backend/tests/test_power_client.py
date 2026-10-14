"""POWER parsing, fill values, cache, retry."""
import json
from datetime import date
from pathlib import Path

import httpx
import pytest
import respx

from backend.app.services.nasa.power import PowerError, fetch_power, parse_power_json

FIXTURE = Path(__file__).parent / "fixtures" / "power_sylhet_sample.json"
URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
ARGS = (24.8949, 91.8687, date(2022, 6, 10), date(2022, 6, 16))


@pytest.fixture
def payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_parse_fixture(payload):
    df = parse_power_json(payload)
    assert list(df.columns) == ["PRECTOTCORR", "T2M_MAX", "RH2M", "GWETROOT"]
    assert len(df) == 7
    assert df.index[0] == df.index.min() and df.index.name == "date"
    assert df.loc["2022-06-12", "PRECTOTCORR"] == 129.42


def test_fill_value_becomes_null(payload):
    payload["properties"]["parameter"]["GWETROOT"]["20220611"] = -999.0
    df = parse_power_json(payload)
    assert df["GWETROOT"].isna().sum() == 1
    assert df.loc["2022-06-11", "GWETROOT"] != df.loc["2022-06-11", "GWETROOT"]


def test_bad_payload_raises():
    with pytest.raises(PowerError):
        parse_power_json({"oops": 1})


@respx.mock
def test_request_params_and_cache(payload, tmp_path):
    route = respx.get(URL).mock(return_value=httpx.Response(200, json=payload))
    df1 = fetch_power(*ARGS, cache_dir=tmp_path)
    df2 = fetch_power(*ARGS, cache_dir=tmp_path)
    assert route.call_count == 1  # second call served from cache
    assert df1.equals(df2)
    q = route.calls[0].request.url.params
    assert q["parameters"] == "PRECTOTCORR,T2M_MAX,RH2M,GWETROOT"
    assert q["community"] == "AG" and q["format"] == "JSON"
    assert q["start"] == "20220610" and q["end"] == "20220616"
    assert len(list(tmp_path.glob("*.json"))) == 1


@respx.mock
def test_retry_then_success(payload, tmp_path):
    route = respx.get(URL).mock(
        side_effect=[httpx.Response(503), httpx.ConnectError("boom"), httpx.Response(200, json=payload)]
    )
    sleeps: list[float] = []
    df = fetch_power(*ARGS, cache_dir=tmp_path, sleep=sleeps.append, backoff=1.0)
    assert route.call_count == 3
    assert sleeps == [1.0, 2.0]
    assert len(df) == 7


@respx.mock
def test_retry_exhausted(tmp_path):
    respx.get(URL).mock(return_value=httpx.Response(500))
    with pytest.raises(PowerError):
        fetch_power(*ARGS, cache_dir=tmp_path, sleep=lambda s: None, retries=3)
    assert list(tmp_path.glob("*.json")) == []
