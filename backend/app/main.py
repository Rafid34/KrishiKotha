"""FastAPI app factory, CORS and router wiring."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import VERSION, get_settings
from .routers import meta


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    app = FastAPI(title="Krishi Kotha", version=VERSION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(meta.router)
    return app


app = create_app()
