"""Assert that .env.example and backend Settings stay in parity (R-017, R-025, Task B5)."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from backend.app.config import REPO_ROOT, Settings, get_settings
from backend.app.services.messaging.handler import hash_phone

ALLOWLIST_PREFIXES = ("VITE_",)


def _load_env_example_keys() -> set[str]:
    env_example_path = REPO_ROOT / ".env.example"
    keys: set[str] = set()
    for raw in env_example_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _ = line.split("=", 1)
        keys.add(key.strip())
    return keys


def test_env_example_and_settings_parity() -> None:
    """Every key in .env.example is a Settings field or allowlisted, and every Settings field is in .env.example."""
    env_keys = _load_env_example_keys()
    allowlisted = {k for k in env_keys if any(k.startswith(p) for p in ALLOWLIST_PREFIXES)}
    expected_settings_keys = {k.lower() for k in (env_keys - allowlisted)}

    actual_settings_fields = set(Settings.model_fields.keys())

    missing_in_settings = expected_settings_keys - actual_settings_fields
    missing_in_env = actual_settings_fields - expected_settings_keys

    assert not missing_in_settings, f"Keys in .env.example missing from Settings: {missing_in_settings}"
    assert not missing_in_env, f"Settings fields missing from .env.example: {missing_in_env}"


def test_phone_hashing_with_salt() -> None:
    """Phone number is hashed as sha256(salt + phone)."""
    settings = get_settings()
    phone = "+8801700000099"
    expected = hashlib.sha256(f"{settings.phone_hash_salt}{phone}".encode("utf-8")).hexdigest()
    assert hash_phone(phone) == expected
