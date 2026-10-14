"""Earthdata Login through `earthaccess` using the environment strategy."""
from __future__ import annotations

import os
from typing import Any

from ...config import get_settings
from .offline import ensure_online


class EarthdataAuthError(RuntimeError):
    """Raised when Earthdata Login fails or credentials are missing."""


def login() -> Any:
    """Log in with `earthaccess.login(strategy="environment")` and return the auth object.

    Credentials come from `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD` (or
    `EARTHDATA_TOKEN`); values from `.env` are exported to the process environment first.
    """
    ensure_online("Earthdata Login")
    import earthaccess

    settings = get_settings()
    if settings.earthdata_username and settings.earthdata_password:
        os.environ.setdefault("EARTHDATA_USERNAME", settings.earthdata_username)
        os.environ.setdefault("EARTHDATA_PASSWORD", settings.earthdata_password)
    try:
        auth = earthaccess.login(strategy="environment")
    except Exception as exc:  # earthaccess raises several unrelated types
        raise EarthdataAuthError(f"Earthdata login failed: {type(exc).__name__}: {exc}") from exc
    if not getattr(auth, "authenticated", False):
        raise EarthdataAuthError("Earthdata login did not authenticate")
    return auth
