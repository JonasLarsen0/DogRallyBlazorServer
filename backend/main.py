"""
RejseplanAPI — Smart Commuter Dashboard backend.

Entry point and FastAPI application factory.

Start with::

    uvicorn backend.main:app --reload
"""

from __future__ import annotations

import json
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.rejseplanen import RejseplaneClient
from backend.api.routes import alerts, config, delays, departures, health, stops
from backend.api.websocket import ConnectionManager
from backend.api.websocket_route import router as ws_router
from backend.config import settings
from backend.services.delay_logger import DelayLogger
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

_RUNTIME_CONFIG_PATH = Path(settings.delay_log_path).parent / "runtime_config.json"


def _load_runtime_config() -> dict | None:
    """Load persisted runtime config from disk, returning None if absent or invalid."""
    try:
        if _RUNTIME_CONFIG_PATH.exists():
            data = json.loads(_RUNTIME_CONFIG_PATH.read_text())
            logger.info("Loaded persisted runtime config from %s", _RUNTIME_CONFIG_PATH)
            return data
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load runtime config from %s: %s", _RUNTIME_CONFIG_PATH, exc)
    return None


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: initialise resources on startup, clean up on shutdown."""

    logger.info("Starting RejseplanAPI backend …")

    # Record startup time for uptime reporting.
    app.state.startup_time = datetime.now(timezone.utc)

    # --- Initialise shared singletons ---
    client = RejseplaneClient(
        api_key=settings.rejseplanen_api_key,
        train_only=settings.train_only,
    )
    manager = ConnectionManager()
    delay_logger = DelayLogger(db_path=settings.delay_log_path)
    poller = DeparturePoller(client=client, manager=manager, delay_logger=delay_logger)

    # Attach to app.state so routes and WebSocket handlers can reach them.
    app.state.rejseplanen_client = client
    app.state.connection_manager = manager
    app.state.delay_logger = delay_logger
    app.state.poller = poller

    # --- Determine effective stop config (persisted runtime config wins) ---
    runtime_cfg = _load_runtime_config()
    if runtime_cfg:
        stop_ids = runtime_cfg.get("stop_ids") or []
        walk_seconds = runtime_cfg.get("walk_time_seconds", settings.walk_time_seconds)
        logger.info("Using persisted runtime config — stops=%s, walk=%ds", stop_ids, walk_seconds)
    else:
        stop_ids = settings.default_stop_ids_list()
        walk_seconds = settings.walk_time_seconds
        if stop_ids:
            logger.info("Starting poller with default stop IDs: %s", stop_ids)
        else:
            logger.warning(
                "No DEFAULT_STOP_IDS configured — poller will start with an empty list. "
                "POST /api/config to add stops at runtime."
            )

    await poller.start(stop_ids, walk_seconds=walk_seconds)

    # --- Startup banner ---
    # Inner content area is 40 chars wide; pad each line to fit the box.
    _W = 40

    def _banner_line(content: str) -> str:
        """Format a single banner line, truncating long content."""
        truncated = content[:_W]
        return f"║  {truncated:<{_W}}║"

    stop_names = ", ".join(stop_ids) if stop_ids else "(none)"
    docs_url = f"http://{settings.host}:{settings.port}/docs"
    banner_lines = [
        "╔" + "═" * (_W + 2) + "╗",
        _banner_line("RejseplanAPI v1.0.0  — ready"),
        _banner_line(f"Stops: {stop_names}"),
        _banner_line(f"Train-only: {settings.train_only}"),
        _banner_line(f"Docs: {docs_url}"),
        "╚" + "═" * (_W + 2) + "╝",
    ]
    for line in banner_lines:
        logger.info(line)

    yield  # <-- application is running

    # --- Shutdown ---
    logger.info("Shutting down RejseplanAPI backend …")
    await poller.stop()
    await delay_logger.close()
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
    app.include_router(delays.router)
    app.include_router(health.router)

    # --- WebSocket ---
    app.include_router(ws_router)

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
