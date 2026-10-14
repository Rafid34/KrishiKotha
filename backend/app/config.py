"""Application settings loaded from environment variables (pydantic-settings)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = REPO_ROOT / "data" / "static"
BASELINE_DIR = REPO_ROOT / "data" / "baseline"
CACHE_DIR = REPO_ROOT / "data" / "cache"
VERSION = "1.0.0"


class Settings(BaseSettings):
    """Runtime configuration; see `.env.example` for every key."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "development"
    database_url: str = f"sqlite:///{(REPO_ROOT / 'data' / 'krishi_kotha.db').as_posix()}"
    admin_api_key: str = "change-me"
    cors_origins: str = "http://localhost:5173"
    data_mode: str = "live"
    earthdata_username: str = ""
    earthdata_password: str = ""
    power_api_base: str = "https://power.larc.nasa.gov/api"
    cmr_base: str = "https://cmr.earthdata.nasa.gov/search"
    bbox_west: float = 88.0
    bbox_south: float = 20.5
    bbox_east: float = 92.7
    bbox_north: float = 26.7
    baseline_start_year: int = 2001
    baseline_end_year: int = 2020

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """Bangladesh bounding box as (west, south, east, north)."""
        return (self.bbox_west, self.bbox_south, self.bbox_east, self.bbox_north)

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS_ORIGINS split on commas."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
