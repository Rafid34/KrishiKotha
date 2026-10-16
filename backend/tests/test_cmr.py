"""Unit tests for NASA CMR granule discovery using respx."""
from datetime import datetime, timezone

import httpx
import pytest
import respx

from backend.app.config import get_settings
from backend.app.services.nasa.cmr import CmrError, latest_granule_date


@respx.mock
def test_cmr_normal_response():
    cmr_url = f"{get_settings().cmr_base.rstrip('/')}/granules.json"
    mock_payload = {
        "feed": {
            "entry": [
                {
                    "title": "SMAP_L4_SM_gpc_20240510T120000_Vv8030_001",
                    "time_start": "2024-05-10T12:00:00Z",
                }
            ]
        }
    }
    route = respx.get(cmr_url).mock(return_value=httpx.Response(200, json=mock_payload))

    dt = latest_granule_date("SPL4SMGP", "008")

    assert dt == datetime(2024, 5, 10, 12, 0, 0, tzinfo=timezone.utc)
    assert route.call_count == 1
    params = route.calls[0].request.url.params
    assert params["short_name"] == "SPL4SMGP"
    assert params["version"] == "008"
    assert params["sort_key"] == "-start_date"
    assert params["page_size"] == "1"


@respx.mock
def test_cmr_empty_result():
    cmr_url = f"{get_settings().cmr_base.rstrip('/')}/granules.json"
    mock_payload = {"feed": {"entry": []}}
    route = respx.get(cmr_url).mock(return_value=httpx.Response(200, json=mock_payload))

    dt = latest_granule_date("NONEXISTENT", "001")

    assert dt is None
    assert route.call_count == 1


@respx.mock
def test_cmr_http_error():
    cmr_url = f"{get_settings().cmr_base.rstrip('/')}/granules.json"
    respx.get(cmr_url).mock(return_value=httpx.Response(500, text="Internal Server Error"))

    with pytest.raises(CmrError, match="failed"):
        latest_granule_date("SPL4SMGP", "008")


@respx.mock
def test_cmr_missing_time_start():
    cmr_url = f"{get_settings().cmr_base.rstrip('/')}/granules.json"
    mock_payload = {"feed": {"entry": [{"title": "some_granule"}]}}
    respx.get(cmr_url).mock(return_value=httpx.Response(200, json=mock_payload))

    with pytest.raises(CmrError, match="has no time_start"):
        latest_granule_date("SPL4SMGP", "008")
