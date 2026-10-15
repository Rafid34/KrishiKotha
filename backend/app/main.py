"""FastAPI app factory: CORS, error format, routers, snapshot loading."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import VERSION, get_settings
from .errors import install_error_handlers
from .routers import advice, backtest, districts, messaging, meta, risk

log = logging.getLogger("krishi_kotha")


def prepare_database() -> None:
    """Create tables, seed static data and, in snapshot mode, load JSON snapshots.

    Snapshot mode only reads local files; it never calls NASA services.
    """
    from .db import SessionLocal, create_all
    from .seed import seed
    from .services.snapshots import load_snapshots

    create_all()
    with SessionLocal() as session:
        seed(session)
        if get_settings().data_mode == "snapshot":
            counts = load_snapshots(session)
            log.info("Loaded snapshots: %s", counts)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Prepare the database before serving requests."""
    prepare_database()
    yield


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    app = FastAPI(title="Krishi Kotha", version=VERSION, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    app.include_router(meta.router)
    app.include_router(districts.router)
    app.include_router(risk.router)
    app.include_router(advice.router)
    app.include_router(messaging.router)
    app.include_router(backtest.router)
    return app


app = create_app()
