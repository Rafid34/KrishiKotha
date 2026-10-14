"""Meta routes: /api/health (more added in later phases)."""
from __future__ import annotations

from fastapi import APIRouter

from ..config import VERSION, get_settings

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness check including the configured data mode."""
    return {"status": "ok", "data_mode": get_settings().data_mode, "version": VERSION}
