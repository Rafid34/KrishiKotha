"""Phase 11: TTS cache, audio route, Twilio flag, webhooks and admin broadcast."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import get_settings
from backend.app.models import MessageLog, RiskSnapshot, Subscriber
from backend.app.services.messaging import tts
from backend.app.services.messaging.sim_gateway import sim_gateway

REPO_ROOT = Path(__file__).resolve().parents[2]
BN_TEXT = "বন্যার ঝুঁকি বেশি।"
FAKE_MP3 = b"ID3-fake-mp3"
DAY = date(2022, 6, 16)
ADMIN = {"X-Admin-Key": "test-admin-key"}  # matches `messaging_env` in conftest.py


@pytest.fixture()
def fake_tts(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace gTTS with a stub and record every text it is asked to speak."""
    calls: list[str] = []

    def fake(text: str) -> bytes:
        calls.append(text)
        return FAKE_MP3

    monkeypatch.setattr(tts, "synthesize", fake)
    return calls


@pytest.fixture()
def offline_tts(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(text: str) -> bytes:
        raise OSError("network unreachable")

    monkeypatch.setattr(tts, "synthesize", fail)


@pytest.fixture()
def snapshots(session_factory: sessionmaker[Session]) -> sessionmaker[Session]:
    """Sylhet in high flood risk, Rajshahi calm, both on 2022-06-16."""
    with session_factory() as db:
        for did, flood in (("sylhet", 90.0), ("rajshahi", 5.0)):
            db.add(
                RiskSnapshot(
                    district_id=did, date=DAY, drought_score=5.0, flood_score=flood,
                    salt_score=2.0, drought_level="low",
                    flood_level="high" if flood >= 70 else "low", salt_level="low",
                    inputs={}, sources={}, degraded=False,
                )
            )
        db.commit()
    return session_factory


def _register(client: TestClient, phone: str, body: str) -> None:
    resp = client.post("/api/sim/sms", json={"from": phone, "body": body, "date": "2022-06-16"})
    assert resp.status_code == 200


# --- TTS cache --------------------------------------------------------------------------


def test_audio_filename_is_sha256_of_text() -> None:
    name = tts.audio_filename(BN_TEXT)
    assert name.endswith(".mp3") and len(name) == 64 + 4
    assert name == tts.audio_filename(BN_TEXT)
    assert name != tts.audio_filename(BN_TEXT + "!")


def test_same_text_triggers_one_tts_call(fake_tts: list[str]) -> None:
    name = tts.register_text(BN_TEXT)
    first = tts.ensure_audio(name)
    second = tts.ensure_audio(tts.register_text(BN_TEXT))
    assert first == second and first.read_bytes() == FAKE_MP3
    assert fake_tts == [BN_TEXT]
    assert first.parent == get_settings().audio_path


def test_ensure_audio_rejects_unregistered_and_malformed(fake_tts: list[str]) -> None:
    with pytest.raises(tts.AudioNotFoundError):
        tts.ensure_audio(tts.audio_filename("never registered"))
    with pytest.raises(tts.AudioNotFoundError):
        tts.ensure_audio("../secret.mp3")
    assert fake_tts == []


def test_offline_tts_raises_and_leaves_no_mp3(offline_tts: None) -> None:
    name = tts.register_text(BN_TEXT)
    with pytest.raises(tts.TtsUnavailableError):
        tts.ensure_audio(name)
    assert not (get_settings().audio_path / name).exists()


# --- /api/audio and /api/advice -----------------------------------------------------------


def test_advice_audio_url_plays_through_audio_route(
    client: TestClient, snapshots: sessionmaker[Session], fake_tts: list[str]
) -> None:
    advice = client.post(
        "/api/advice", json={"district_id": "sylhet", "crop_id": "aman", "date": "2022-06-16"}
    ).json()
    assert fake_tts == []  # advice only registers text; no TTS call yet
    assert advice["audio_url"] == tts.audio_url(tts.audio_filename(advice["text_bn"]))

    resp = client.get(advice["audio_url"])
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"
    assert resp.content == FAKE_MP3
    client.get(advice["audio_url"])
    assert len(fake_tts) == 1


def test_advice_has_no_audio_url_when_tts_disabled(
    client: TestClient, snapshots: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TTS_ENABLED", "false")
    get_settings.cache_clear()
    advice = client.post(
        "/api/advice", json={"district_id": "sylhet", "crop_id": "aman", "date": "2022-06-16"}
    ).json()
    assert advice["audio_url"] is None


def test_audio_route_503_when_gtts_offline(client: TestClient, offline_tts: None) -> None:
    name = tts.register_text(BN_TEXT)
    resp = client.get(tts.audio_url(name))
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "unavailable"
    assert "Text to speech failed" in resp.json()["error"]["message"]


def test_audio_route_404_for_unknown_or_malformed_names(client: TestClient) -> None:
    assert client.get(tts.audio_url(tts.audio_filename("unknown"))).status_code == 404
    assert client.get("/api/audio/notahash.mp3").status_code == 404
    assert client.get("/api/audio/..%2Fsecret.mp3").status_code == 404


# --- Twilio flag --------------------------------------------------------------------------


def test_startup_with_twilio_disabled_imports_no_twilio() -> None:
    code = (
        "import sys; import backend.app.main; "
        "bad = [m for m in ('twilio', 'gtts') if m in sys.modules]; "
        "print('IMPORTED:' + ','.join(bad)); sys.exit(1 if bad else 0)"
    )
    env = {**os.environ, "TWILIO_ENABLED": "false"}
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=REPO_ROOT, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_webhooks_404_when_twilio_disabled(client: TestClient) -> None:
    assert client.post("/api/sms/inbound", data={"From": "+8801", "Body": "HELP"}).status_code == 404
    assert client.post("/api/voice/inbound", data={"From": "+8801"}).status_code == 404


PUBLIC_URL = "https://demo.example.test"
TWILIO_TOKEN = "twilio-test-token"


@pytest.fixture()
def twilio_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TWILIO_ENABLED", "true")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TWILIO_TOKEN)
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15005550006")
    monkeypatch.setenv("PUBLIC_BASE_URL", PUBLIC_URL)
    get_settings.cache_clear()


def _signed(path: str, params: dict[str, str]) -> dict[str, str]:
    from twilio.request_validator import RequestValidator

    return {"X-Twilio-Signature": RequestValidator(TWILIO_TOKEN).compute_signature(PUBLIC_URL + path, params)}


def test_sms_inbound_rejects_bad_signature(client: TestClient, twilio_on: None) -> None:
    params = {"From": "+8801700000001", "Body": "HELP"}
    assert client.post("/api/sms/inbound", data=params).status_code == 403
    bad = {"X-Twilio-Signature": "AAAA"}
    assert client.post("/api/sms/inbound", data=params, headers=bad).status_code == 403


def test_sms_inbound_returns_twiml(
    client: TestClient, twilio_on: None, snapshots: sessionmaker[Session]
) -> None:
    params = {"From": "+8801700000001", "Body": "HELP"}
    resp = client.post("/api/sms/inbound", data=params, headers=_signed("/api/sms/inbound", params))
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/xml")
    assert "<Response><Message>" in resp.text
    assert "SYLHET AMAN" in resp.text
    with snapshots() as db:
        assert db.query(MessageLog).filter_by(channel="sms").count() == 1


def test_voice_inbound_plays_cached_mp3_via_public_url(
    client: TestClient, twilio_on: None, snapshots: sessionmaker[Session], fake_tts: list[str]
) -> None:
    _register(client, "+8801700000002", "SYLHET AMAN")
    params = {"From": "+8801700000002"}
    resp = client.post("/api/voice/inbound", data=params, headers=_signed("/api/voice/inbound", params))
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/xml")
    assert f"<Play>{PUBLIC_URL}/api/audio/" in resp.text and ".mp3</Play>" in resp.text
    assert len(fake_tts) == 1


def test_voice_inbound_falls_back_to_say_when_tts_offline(
    client: TestClient, twilio_on: None, offline_tts: None
) -> None:
    params = {"From": "+8801700000003"}
    resp = client.post("/api/voice/inbound", data=params, headers=_signed("/api/voice/inbound", params))
    assert resp.status_code == 200
    assert "<Say" in resp.text and "<Play>" not in resp.text


# --- Admin broadcast ----------------------------------------------------------------------


BROADCAST = {"district_id": "sylhet", "min_level": "moderate", "dry_run": True}


def test_admin_requires_key(client: TestClient) -> None:
    assert client.post("/api/admin/broadcast", json=BROADCAST).status_code == 401
    wrong = {"X-Admin-Key": "wrong"}
    resp = client.post("/api/admin/broadcast", json=BROADCAST, headers=wrong)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_admin_rejects_everything_when_key_unset(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ADMIN_API_KEY", "")
    get_settings.cache_clear()
    assert client.post("/api/admin/broadcast", json=BROADCAST, headers={"X-Admin-Key": ""}).status_code == 401


def test_broadcast_dry_run_counts_and_sends_nothing(
    client: TestClient, snapshots: sessionmaker[Session]
) -> None:
    sim_gateway.clear()
    _register(client, "+8801700000010", "SYLHET AMAN")
    _register(client, "+8801700000011", "SYLHET BORO")
    _register(client, "+8801700000012", "RAJSHAHI AMAN")
    with snapshots() as db:
        logs_before = db.query(MessageLog).count()

    body = {"district_id": "sylhet", "min_level": "moderate", "date": "2022-06-16"}  # dry_run omitted
    resp = client.post("/api/admin/broadcast", json=body, headers=ADMIN)
    assert resp.status_code == 200
    data = resp.json()
    assert data["sent"] == 0
    assert data["recipients"] == 2
    assert "বন্যার ঝুঁকি বেশি" in data["sample_text_bn"]
    assert sim_gateway.sent_messages == []
    with snapshots() as db:
        assert db.query(MessageLog).count() == logs_before


def test_broadcast_min_level_and_inactive_subscribers(
    client: TestClient, snapshots: sessionmaker[Session]
) -> None:
    _register(client, "+8801700000020", "SYLHET AMAN")
    _register(client, "+8801700000021", "SYLHET AMAN")
    client.post("/api/sim/sms", json={"from": "+8801700000021", "body": "STOP"})
    body = {"district_id": "sylhet", "min_level": "high", "date": "2022-06-16"}
    assert client.post("/api/admin/broadcast", json=body, headers=ADMIN).json()["recipients"] == 1

    calm = {"district_id": "rajshahi", "min_level": "moderate", "date": "2022-06-16"}
    _register(client, "+8801700000022", "RAJSHAHI AMAN")
    data = client.post("/api/admin/broadcast", json=calm, headers=ADMIN).json()
    assert data == {"recipients": 0, "sample_text_bn": None, "sent": 0}


def test_broadcast_live_send_uses_simulator_gateway_when_twilio_off(
    client: TestClient, snapshots: sessionmaker[Session]
) -> None:
    sim_gateway.clear()
    _register(client, "+8801700000030", "SYLHET AMAN")
    body = {"district_id": "sylhet", "min_level": "moderate", "dry_run": False, "date": "2022-06-16"}
    data = client.post("/api/admin/broadcast", json=body, headers=ADMIN).json()
    assert data["recipients"] == 1 and data["sent"] == 1
    assert [m.to for m in sim_gateway.sent_messages] == ["+8801700000030"]
    with snapshots() as db:
        assert db.query(Subscriber).count() == 1
        assert db.query(MessageLog).filter_by(channel="sim", rule_id="flood_high_early").count() >= 1
    sim_gateway.clear()


def test_broadcast_unknown_district_404(client: TestClient) -> None:
    body = {"district_id": "nowhere"}
    assert client.post("/api/admin/broadcast", json=body, headers=ADMIN).status_code == 404
