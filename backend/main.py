"""
RejseplanAPI — Smart Commuter Dashboard backend.

Entry point and FastAPI application factory.

Start with::

    uvicorn backend.main:app --reload
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.rejseplanen import RejseplaneClient
from backend.api.routes import alerts, config, departures, stops
from backend.api.websocket import ConnectionManager
from backend.api.websocket_route import router as ws_router
from backend.config import settings
from backend.services.poller import DeparturePoller

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: initialise resources on startup, clean up on shutdown."""

    logger.info("Starting RejseplanAPI backend …")

    # --- Initialise shared singletons ---
    client = RejseplaneClient(api_key=settings.rejseplanen_api_key)
    manager = ConnectionManager()
    poller = DeparturePoller(client=client, manager=manager)

    # Attach to app.state so routes and WebSocket handlers can reach them.
    app.state.rejseplanen_client = client
    app.state.connection_manager = manager
    app.state.poller = poller

    # --- Start background polling ---
    stop_ids = settings.default_stop_ids_list()
    if stop_ids:
        logger.info("Starting poller with default stop IDs: %s", stop_ids)
    else:
        logger.warning(
            "No DEFAULT_STOP_IDS configured — poller will start with an empty list. "
            "POST /api/config to add stops at runtime."
        )

    await poller.start(stop_ids, walk_seconds=settings.walk_time_seconds)

    logger.info(
        "RejseplanAPI ready — http://%s:%d  |  WS ws://%s:%d/ws",
        settings.host,
        settings.port,
        settings.host,
        settings.port,
    )

    yield  # <-- application is running

    # --- Shutdown ---
    logger.info("Shutting down RejseplanAPI backend …")
    await poller.stop()
    await client.aclose()
    logger.info("Shutdown complete")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="RejseplanAPI — Smart Commuter Dashboard",
        description=(
            "Real-time public transport departures powered by Rejseplanen API 2.0. "
            "Provides REST endpoints for HA custom integrations and a WebSocket feed "
            "for live dashboard updates."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # --- CORS ---
    origins = settings.cors_origins_list()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- REST routers ---
    app.include_router(stops.router)
    app.include_router(departures.router)
    app.include_router(alerts.router)
    app.include_router(config.router)

    # --- WebSocket ---
    app.include_router(ws_router)

    # --- Health check ---
    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        """Simple liveness probe."""
        return {"status": "ok"}

    return app


app = create_app()


# ---------------------------------------------------------------------------
# Dev-mode entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info",
    )
