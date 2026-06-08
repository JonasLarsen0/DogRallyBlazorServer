# Development Guide

How to run RejseplanAPI locally without Docker, contribute changes, and understand the codebase.

---

## Prerequisites

| Tool | Minimum version | Check |
|---|---|---|
| Python | 3.11 | `python --version` |
| Node.js | 20 | `node --version` |
| npm | 9 | `npm --version` |
| git | any | `git --version` |

You will also need a Rejseplanen API key for the backend to return real data. See [README.md § Getting an API key](../README.md#getting-an-api-key).

---

## Backend (FastAPI)

### Setup

```bash
# Clone the repository
git clone https://github.com/jonaslarsen0/dograllyblazorserver.git
cd dograllyblazorserver

# Create a virtual environment (keep project dependencies isolated)
python -m venv .venv

# Activate it
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows PowerShell
# source .venv/Scripts/activate    # Windows Git Bash

# Install dependencies
pip install -r backend/requirements.txt

# Copy and configure .env
cp .env.example .env
```

Edit `.env` — at minimum set `REJSEPLANEN_API_KEY`. For local development you can set `DEFAULT_STOP_IDS=8600020` (Odense) to get data immediately on startup.

### Run the dev server

```bash
# From the project root (important — the import paths use backend.*)
uvicorn backend.main:app --reload
```

The backend starts at `http://localhost:8000`.

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/health`
- WebSocket: `ws://localhost:8000/ws`

`--reload` watches for file changes and restarts automatically. The WebSocket connection will drop briefly on restart — the frontend reconnects automatically.

### Alternate: run as a module

```bash
python -m backend.main
```

This uses the `if __name__ == "__main__"` block in `main.py`, which runs uvicorn programmatically. Useful for debugging with an IDE.

---

## Frontend (SvelteKit)

### Setup

```bash
cd frontend
npm install
```

### Run the dev server

```bash
npm run dev
```

The frontend starts at `http://localhost:5173` with hot module replacement (HMR).

For the frontend to work it needs the backend running at `http://localhost:8000`. The SvelteKit dev server proxies WebSocket connections and API calls to the backend — check `svelte.config.js` for the proxy configuration.

### Build for production

```bash
npm run build
```

The production build is output to `frontend/build/`. In Docker this is served by `node build` (the SvelteKit Node adapter).

### Preview the production build locally

```bash
npm run preview
```

---

## Running Tests

### Backend tests

Tests are written with `pytest` and `pytest-asyncio`.

```bash
# From the project root, with the virtual environment activated
pip install pytest pytest-asyncio pytest-httpx

# Run all backend tests
pytest tests/backend/ -v

# Run a specific test file
pytest tests/backend/test_delay_logger.py -v

# Run with coverage
pip install pytest-cov
pytest tests/backend/ --cov=backend --cov-report=term-missing
```

### Home Assistant integration tests

HA integration tests require `pytest-homeassistant-custom-component`:

```bash
pip install pytest-homeassistant-custom-component

pytest tests/ha/ -v
```

### Frontend tests

```bash
cd frontend
npm run test        # Run tests once
npm run test:watch  # Watch mode
```

---

## Project Structure

```
rejseplanapi/
│
├── backend/                        # FastAPI application
│   │
│   ├── api/
│   │   ├── rejseplanen.py          # Async HTTP client wrapping Rejseplanen API 2.0
│   │   │                           # Uses httpx.AsyncClient as base class.
│   │   │                           # All methods return empty collections on errors
│   │   │                           # so the rest of the app stays alive on API failures.
│   │   │
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── stops.py            # GET /api/stops/search
│   │   │   ├── departures.py       # GET /api/departures/{id}
│   │   │   │                       # POST /api/departures/favorites
│   │   │   ├── alerts.py           # GET /api/alerts
│   │   │   ├── config.py           # GET/POST /api/config
│   │   │   └── delays.py           # GET /api/delays
│   │   │                           # GET /api/delays/summary
│   │   │
│   │   ├── websocket.py            # ConnectionManager: tracks connected WS clients
│   │   │                           # and broadcasts JSON payloads to all of them
│   │   └── websocket_route.py      # WS /ws endpoint: connects client, pushes
│   │                               # last cached snapshot, then waits
│   │
│   ├── models/
│   │   ├── departure.py            # Departure, StopDepartures, Alert (Pydantic v2)
│   │   │                           # delay_minutes is a @computed_field
│   │   └── stop.py                 # Stop
│   │
│   ├── services/
│   │   ├── poller.py               # DeparturePoller: asyncio background task
│   │   │                           # Polls all watched stops every N seconds,
│   │   │                           # feeds boards to DelayLogger, broadcasts WS
│   │   │
│   │   └── delay_logger.py         # DelayLogger: detects departures that left with
│   │                               # >= 30 min delay and writes them to SQLite.
│   │                               # Uses a 90-second confirmation window to avoid
│   │                               # false positives from transient API gaps.
│   │
│   ├── config.py                   # Pydantic BaseSettings loaded from .env
│   ├── main.py                     # App factory + lifespan (startup/shutdown)
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                       # SvelteKit application
│   │
│   ├── src/
│   │   ├── app.html                # HTML shell
│   │   │
│   │   ├── lib/
│   │   │   ├── components/
│   │   │   │   ├── DepartureBoard.svelte    # Table of upcoming departures
│   │   │   │   ├── DepartureRow.svelte      # Single departure row with delay badge
│   │   │   │   ├── GoNowAlert.svelte        # Full-screen overlay for imminent trains
│   │   │   │   ├── DisturbancePanel.svelte  # Collapsible HIM alerts panel
│   │   │   │   ├── ConnectionStatus.svelte  # WS connected/reconnecting indicator
│   │   │   │   ├── FlipClock.svelte         # Departure board style flip-digit clock
│   │   │   │   ├── FlipDigit.svelte         # Individual animated flip digit
│   │   │   │   └── LineTypeBadge.svelte     # Coloured badge: IC / RE / S-tog etc.
│   │   │   │
│   │   │   ├── stores/
│   │   │   │   ├── websocket.ts    # Svelte stores fed by the WebSocket connection
│   │   │   │   │                   # Exports: departures, alerts, connected, lastUpdated,
│   │   │   │   │                   # goNowDepartures (derived)
│   │   │   │   └── config.ts       # UI config stores: activeStopIndex, walkTimeSeconds,
│   │   │   │                       # dismissedGoNow (localStorage-persisted)
│   │   │   │
│   │   │   └── utils/
│   │   │       └── time.ts         # Time formatting helpers
│   │   │
│   │   └── routes/
│   │       ├── +layout.svelte      # Root layout (font loading, global reset)
│   │       └── +page.svelte        # Main dashboard: clock, stop tabs, departure board,
│   │                               # GoNow overlay, disturbance ticker
│   │
│   ├── src/tests/                  # Vitest unit tests for Svelte stores
│   ├── Dockerfile                  # Multi-stage: builder (npm run build) + runtime (node)
│   ├── svelte.config.js            # SvelteKit config with Node adapter + dev proxy
│   └── package.json
│
├── ha-integration/
│   └── custom_components/
│       └── rejseplan/
│           ├── __init__.py         # async_setup_entry: creates coordinator, platforms
│           ├── config_flow.py      # Three-step UI flow: URL → search → configure
│           │                       # Also has OptionsFlow for walk_time updates
│           ├── coordinator.py      # DataUpdateCoordinator: fetches /api/departures/{id}
│           │                       # every 30 s, parses into RejseplanDepartureData
│           ├── sensor.py           # NextDepartureSensor, DelayMinutesSensor,
│           │                       # MinutesUntilSensor
│           ├── binary_sensor.py    # GoNowBinarySensor, CancelledBinarySensor
│           ├── const.py            # Domain, config keys, defaults
│           └── manifest.json       # HA integration metadata
│
├── nginx/
│   └── nginx.conf                  # Reverse proxy rules:
│                                   # /api/* → backend:8000
│                                   # /ws    → backend:8000 (WebSocket upgrade)
│                                   # /      → frontend:3000
│
├── tests/
│   ├── backend/
│   │   ├── conftest.py             # Shared fixtures (e.g. mock httpx responses)
│   │   ├── test_rejseplanen.py     # Tests for the API client
│   │   ├── test_models.py          # Tests for Pydantic model behaviour
│   │   └── test_delay_logger.py    # Tests for delay detection logic
│   └── ha/
│       ├── test_coordinator.py     # Tests for HA coordinator parsing
│       └── test_config_flow.py     # Tests for config flow steps
│
├── docker-compose.yml              # Three-service stack: backend, frontend, nginx
├── .env.example                    # Template for .env — all supported variables
└── README.md
```

---

## Architecture Notes

### Why the delay logger waits 90 seconds

Rejseplanen removes a departure from the board when the train physically departs (or when the board window scrolls). The logger cannot tell the difference between "train left" and "train scrolled out of the 20-result window". The workaround:

1. When a departure vanishes from the board, check whether its expected time is plausibly in the past (within the last 3 hours, and not more than 5 minutes in the future).
2. If yes, schedule a write 90 seconds later (= 3 poll cycles).
3. If the departure reappears within those 90 seconds, cancel the write — it was just a transient API gap.

This gives a clean signal with very low false-positive rate.

### Why the HA coordinator does not use the WebSocket

The Home Assistant integration uses polling (`GET /api/departures/{stop_id}` every 30 seconds) rather than the WebSocket feed. This is intentional: Home Assistant's `DataUpdateCoordinator` is built around polling intervals, and a persistent WebSocket connection from HA adds complexity without meaningful benefit at 30-second granularity.

### Data flow summary

```
Rejseplanen API
       ↓  (httpx, every POLL_INTERVAL_SECONDS)
RejseplaneClient.get_multi_departures()
       ↓
DeparturePoller._do_poll()
       ├──→ DelayLogger.process_board()  →  SQLite (for delays >= 30 min)
       └──→ ConnectionManager.broadcast_departures()  →  WebSocket clients
```

HTTP REST endpoints (`/api/departures/{id}` etc.) call the same `RejseplaneClient` directly — they are not served from the poller's cache. This means an HA coordinator fetch always gets fresh data, even if the poller is running at a slower interval.

---

## Adding a New Endpoint

1. Create a route file in `backend/api/routes/` (copy `stops.py` as a template).
2. Add a Pydantic response model if needed, or reuse from `backend/models/`.
3. Register the router in `backend/main.py` with `app.include_router(yourrouter.router)`.
4. Write a test in `tests/backend/`.
5. Document it in `docs/API.md` and the API Reference section of `README.md`.

---

## Code Style

- Python: formatted with `ruff format`, linted with `ruff check`. Run `ruff check . && ruff format .` before committing.
- TypeScript/Svelte: formatted with Prettier (`npm run format` in `frontend/`).
- All Python files use `from __future__ import annotations` for forward-compatible type hints.
- Docstrings follow the `::` reStructuredText convention used by Sphinx.
