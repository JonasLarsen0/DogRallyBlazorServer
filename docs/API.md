# API Reference

Complete endpoint reference for the RejseplanAPI backend (FastAPI, port 8000).

Interactive documentation is also available at runtime:
- Swagger UI: `http://localhost/docs`
- ReDoc: `http://localhost/redoc`

All endpoints are prefixed with `/api/` except the health check (`/health`) and the WebSocket endpoint (`/ws`).

---

## Stops

### `GET /api/stops/search`

Search for stops and stations by name fragment. Calls Rejseplanen's `location.name` endpoint and returns up to 10 matches.

**Query parameters**

| Parameter | Type | Required | Constraints | Description |
|---|---|---|---|---|
| `q` | string | yes | min length 1 | Name fragment to search for |

**Response** — `200 OK`, array of Stop objects

```json
[
  {
    "id": "8600020",
    "name": "Odense St.",
    "lat": 55.40402,
    "lon": 10.40237,
    "stop_type": "ST"
  }
]
```

**Error responses**

| Status | Meaning |
|---|---|
| `422 Unprocessable Entity` | `q` param missing or empty |
| `502 Bad Gateway` | Rejseplanen upstream returned an error |

**curl example**

```bash
curl "http://localhost/api/stops/search?q=Odense"
```

---

## Departures

### `GET /api/departures/{stop_id}`

Fetch the live departure board for a single stop. Makes a direct (uncached) request to Rejseplanen on every call.

**Path parameters**

| Parameter | Type | Description |
|---|---|---|
| `stop_id` | string | Rejseplanen stop ID |

**Response** — `200 OK`, StopDepartures object

```json
{
  "stop_id": "8600020",
  "stop_name": "Odense St.",
  "fetched_at": "2026-06-08T07:42:00.123456+00:00",
  "departures": [
    {
      "stop_id": "8600020",
      "stop_name": "Odense St.",
      "line": "IC",
      "direction": "København H",
      "planned_time": "2026-06-08T07:48:00+02:00",
      "expected_time": "2026-06-08T07:51:00+02:00",
      "cancelled": false,
      "vehicle_type": "IC",
      "track": "3",
      "journey_id": "IC_1234_2026-06-08",
      "delay_minutes": 3
    },
    {
      "stop_id": "8600020",
      "stop_name": "Odense St.",
      "line": "RE",
      "direction": "Fredericia",
      "planned_time": "2026-06-08T07:53:00+02:00",
      "expected_time": null,
      "cancelled": false,
      "vehicle_type": "RE",
      "track": "1",
      "journey_id": "RE_5678_2026-06-08",
      "delay_minutes": 0
    }
  ]
}
```

`delay_minutes` is a computed field: `round((expected_time - planned_time).total_seconds() / 60)`. Returns `0` when `expected_time` is null (no real-time data available).

`expected_time` is null when Rejseplanen has no real-time data for the departure (e.g. the train has not entered the tracking window yet).

**Error responses**

| Status | Meaning |
|---|---|
| `502 Bad Gateway` | Rejseplanen upstream error |

**curl example**

```bash
curl "http://localhost/api/departures/8600020"
```

---

### `POST /api/departures/favorites`

Fetch departure boards for multiple stops in one request. Uses Rejseplanen's `multiDepartureBoard` endpoint where available; falls back to parallel individual requests on HTTP 400/404.

**Request body**

```json
{
  "stop_ids": ["8600020", "8600254", "8600868"]
}
```

An empty `stop_ids` list returns an empty array immediately (no upstream calls).

**Response** — `200 OK`, array of StopDepartures objects (same schema as single-stop endpoint)

**curl example**

```bash
curl -X POST "http://localhost/api/departures/favorites" \
  -H "Content-Type: application/json" \
  -d '{"stop_ids": ["8600020", "8600254"]}'
```

---

## Alerts

### `GET /api/alerts`

Return currently active HIM (Hafas Information Manager) service disruption messages from Rejseplanen. Returns an empty array when there are no active alerts or when the upstream call fails.

**No parameters**

**Response** — `200 OK`, array of Alert objects

```json
[
  {
    "id": "him_9182",
    "summary": "Forsinkelser på strækningen Odense–København pga. sporarbejde",
    "affected_lines": ["IC", "ICE"],
    "valid_from": "2026-06-08T06:00:00+02:00",
    "valid_to": "2026-06-08T22:00:00+02:00",
    "severity": "2"
  }
]
```

`severity` is the raw `priority` field from Rejseplanen. Lower values typically indicate higher severity, but the exact mapping is not published by Rejseplanen.

**curl example**

```bash
curl "http://localhost/api/alerts"
```

---

## Config

### `GET /api/config`

Return the current runtime poller configuration. Note: `poll_interval_seconds` cannot be changed at runtime; it is read from the environment variable and requires a container restart to change.

**Response** — `200 OK`

```json
{
  "stop_ids": ["8600020", "8600254"],
  "walk_time_seconds": 300,
  "poll_interval_seconds": 30
}
```

**curl example**

```bash
curl "http://localhost/api/config"
```

---

### `POST /api/config`

Update watched stop IDs and/or walk time. Takes effect immediately — the poller restarts on the next request cycle. Stop IDs and walk time set this way are not persisted across container restarts; set `DEFAULT_STOP_IDS` and `WALK_TIME_SECONDS` in `.env` for persistence.

**Request body**

| Field | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `stop_ids` | array of strings | `[]` | — | Rejseplanen stop IDs to watch |
| `walk_time_seconds` | integer | `300` | >= 0 | Walk time to stop in seconds |

```json
{
  "stop_ids": ["8600020", "8600254", "8600868"],
  "walk_time_seconds": 420
}
```

**Response** — `200 OK`, updated config (same schema as `GET /api/config`)

**curl example**

```bash
curl -X POST "http://localhost/api/config" \
  -H "Content-Type: application/json" \
  -d '{"stop_ids": ["8600020", "8600254"], "walk_time_seconds": 420}'
```

---

## Delays

### `GET /api/delays`

Query the delay compensation log. Returns delays that breached the `min_tier` threshold. Results are ordered by `planned_time` descending (most recent first).

**Query parameters**

| Parameter | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `date_from` | string | — | `YYYY-MM-DD` | Filter from date, inclusive |
| `date_to` | string | — | `YYYY-MM-DD` | Filter to date, inclusive |
| `stop_id` | string | — | — | Filter by Rejseplanen stop ID |
| `min_tier` | integer | `30` | `30`, `60`, or `90` | Minimum delay tier |
| `line` | string | — | — | Filter by line name (exact match, e.g. `IC`) |
| `limit` | integer | `100` | 1–500 | Page size |
| `offset` | integer | `0` | >= 0 | Pagination offset |

**Response** — `200 OK`

```json
{
  "total": 1,
  "offset": 0,
  "limit": 100,
  "results": [
    {
      "id": 47,
      "journey_id": "IC_1234_2026-06-03",
      "stop_id": "8600020",
      "stop_name": "Odense St.",
      "line": "IC",
      "direction": "København H",
      "vehicle_type": "IC",
      "planned_time": "2026-06-03T07:48:00+00:00",
      "actual_time": "2026-06-03T08:52:00+00:00",
      "delay_minutes": 64,
      "delay_tier": 60,
      "logged_at": "2026-06-03T08:53:14.221000+00:00",
      "log_date": "2026-06-03"
    }
  ]
}
```

`total` reflects the number of results in this response, not the full dataset count. Use `offset` + `limit` for pagination.

`delay_tier` is the highest threshold breached: `30`, `60`, or `90`. A delay of 73 minutes gets tier `60` (not `30`).

`planned_time` and `actual_time` are stored as UTC ISO-8601 strings.

**curl examples**

```bash
# All 60+ minute delays in June 2026 at Odense
curl "http://localhost/api/delays?date_from=2026-06-01&date_to=2026-06-30&stop_id=8600020&min_tier=60"

# IC line delays, last 7 days, paginated
curl "http://localhost/api/delays?date_from=2026-06-01&line=IC&limit=20&offset=0"

# Everything logged (all tiers)
curl "http://localhost/api/delays?min_tier=30&limit=500"
```

---

### `GET /api/delays/summary`

Per-stop, per-tier counts for the last 30 days. Does not support filters; use `GET /api/delays` for filtered queries.

**Response** — `200 OK`

```json
{
  "rows": [
    { "stop_name": "Nyborg St.", "delay_tier": 30, "count": 2 },
    { "stop_name": "Odense St.", "delay_tier": 30, "count": 8 },
    { "stop_name": "Odense St.", "delay_tier": 60, "count": 3 },
    { "stop_name": "Odense St.", "delay_tier": 90, "count": 1 }
  ]
}
```

Results are ordered by `stop_name`, then `delay_tier`.

**curl example**

```bash
curl "http://localhost/api/delays/summary"
```

---

## Health

### `GET /health`

Liveness probe. Used by the Docker `healthcheck` directive.

**Response** — `200 OK`

```json
{ "status": "ok" }
```

**curl example**

```bash
curl "http://localhost/health"
```

---

## WebSocket

### `WS /ws`

Connect to receive live departure board updates on every polling cycle.

**URL:** `ws://your-host/ws` (proxied through nginx; raw backend: `ws://localhost:8000/ws`)

**Protocol:**
1. Client connects — server sends the last cached snapshot immediately (if one exists)
2. Server pushes a new JSON message after each completed poll cycle
3. The client is read-only — messages sent by the client are discarded
4. Connection is kept alive until the client disconnects

**Message envelope**

```json
{
  "type": "departures_update",
  "timestamp": "2026-06-08T07:42:00.000000+00:00",
  "walk_seconds": 300,
  "stops": [ /* array of StopDepartures with extra fields, see below */ ],
  "alerts": [ /* array of Alert objects */ ]
}
```

Each departure in `stops[].departures` has two extra computed fields added by the poller at broadcast time:

| Field | Type | Description |
|---|---|---|
| `seconds_until` | integer | Seconds from broadcast time until the expected departure |
| `go_now` | boolean | `true` when `0 < seconds_until <= walk_seconds` |

**JavaScript example**

```javascript
const ws = new WebSocket('ws://localhost/ws');

ws.onmessage = (event) => {
  const payload = JSON.parse(event.data);
  if (payload.type === 'departures_update') {
    payload.stops.forEach(stop => {
      stop.departures.forEach(dep => {
        console.log(`${dep.line} → ${dep.direction}: ${dep.seconds_until}s (go_now: ${dep.go_now})`);
      });
    });
  }
};
```

---

## Data Models

### Stop

| Field | Type | Description |
|---|---|---|
| `id` | string | Rejseplanen stop ID |
| `name` | string | Display name |
| `lat` | float \| null | Latitude (WGS84) |
| `lon` | float \| null | Longitude (WGS84) |
| `stop_type` | string | Rejseplanen type string (`ST`, `ADR`, `POI`) |

### Departure

| Field | Type | Description |
|---|---|---|
| `stop_id` | string | Stop this departure is from |
| `stop_name` | string | Stop display name |
| `line` | string | Line identifier (e.g. `IC`, `RE 67`) |
| `direction` | string | End destination of this service |
| `planned_time` | datetime | Scheduled departure (Copenhagen TZ / ISO-8601) |
| `expected_time` | datetime \| null | Real-time departure (null = no RT data) |
| `cancelled` | boolean | `true` if the departure is cancelled |
| `vehicle_type` | string | Vehicle type string from Rejseplanen (e.g. `IC`, `S`) |
| `track` | string \| null | Platform/track number |
| `journey_id` | string | Unique journey identifier from Rejseplanen |
| `delay_minutes` | integer | Computed: `round((expected - planned) / 60)`, 0 if no RT data |

### Alert

| Field | Type | Description |
|---|---|---|
| `id` | string | HIM message ID |
| `summary` | string | Short description of the disruption |
| `affected_lines` | array of strings | Line names affected |
| `valid_from` | datetime \| null | When the alert becomes active |
| `valid_to` | datetime \| null | When the alert expires |
| `severity` | string | Raw priority field from Rejseplanen |
