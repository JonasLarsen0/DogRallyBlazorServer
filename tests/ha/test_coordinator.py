"""Tests for RejseplanCoordinator."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STOP_ID = "8600020"
API_URL = "http://localhost:8000"

# A future datetime far enough ahead that it will not be filtered out
_FUTURE_ISO = "2099-01-01T12:00:00+00:00"
_FUTURE_LATE_ISO = "2099-01-01T12:05:00+00:00"  # 5 min later (delay)

SAMPLE_RESPONSE = {
    "stop_id": STOP_ID,
    "stop_name": "Odense St.",
    "departures": [
        {
            "journey_id": "abc123",
            "stop_id": STOP_ID,
            "stop_name": "Odense St.",
            "line": "IC 123",
            "direction": "København H",
            "planned_time": _FUTURE_ISO,
            "expected_time": _FUTURE_LATE_ISO,
            "delay_minutes": 5,
            "cancelled": False,
            "vehicle_type": "IC",
            "track": "3",
            "fetched_at": "2026-06-08T09:55:00+00:00",
        }
    ],
    "fetched_at": "2026-06-08T09:55:00+00:00",
}


def _make_mock_response(payload: dict, status: int = 200) -> MagicMock:
    """Return an async context-manager mock that yields a response."""
    response = AsyncMock()
    response.status = status
    response.json = AsyncMock(return_value=payload)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _make_error_response(exc: Exception) -> MagicMock:
    """Return an async context-manager mock that raises *exc* on __aenter__."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(side_effect=exc)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _make_coordinator(
    hass,
    line_filter: str = "",
    walk_time_minutes: int = 5,
) -> "RejseplanCoordinator":  # noqa: F821
    from custom_components.rejseplan.coordinator import RejseplanCoordinator

    session = MagicMock(spec=aiohttp.ClientSession)
    coordinator = RejseplanCoordinator(
        hass=hass,
        api_url=API_URL,
        stop_id=STOP_ID,
        stop_name="Odense St.",
        line_filter=line_filter,
        walk_time_minutes=walk_time_minutes,
        session=session,
    )
    return coordinator


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_fetch_and_parse(hass):
    """Coordinator parses the API envelope and returns correct departure data."""
    coordinator = _make_coordinator(hass)
    coordinator._session.get.return_value = _make_mock_response(SAMPLE_RESPONSE)

    data = await coordinator._async_update_data()

    assert data is not None
    assert data.line == "IC 123"
    assert data.direction == "København H"
    assert data.delay_minutes == 5
    assert data.track == "3"
    assert data.vehicle_type == "IC"
    assert data.cancelled is False
    assert data.next_departure_dt is not None


@pytest.mark.asyncio
async def test_connection_error_returns_previous_data(hass):
    """On ClientError, previous data is returned instead of raising UpdateFailed."""
    coordinator = _make_coordinator(hass)

    # Prime coordinator with valid data
    coordinator._session.get.return_value = _make_mock_response(SAMPLE_RESPONSE)
    previous = await coordinator._async_update_data()
    coordinator.data = previous

    # Now simulate a connection error
    coordinator._session.get.return_value = _make_error_response(
        aiohttp.ClientConnectorError(MagicMock(), MagicMock())
    )

    result = await coordinator._async_update_data()
    # Should return the cached data, not raise
    assert result is previous


@pytest.mark.asyncio
async def test_connection_error_no_previous_data_raises(hass):
    """On ClientError with no cached data, UpdateFailed is raised."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    coordinator = _make_coordinator(hass)
    coordinator.data = None

    coordinator._session.get.return_value = _make_error_response(
        aiohttp.ClientConnectorError(MagicMock(), MagicMock())
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_line_filter_partial_match(hass):
    """line_filter='IC' should match a departure with line='IC 123'."""
    coordinator = _make_coordinator(hass, line_filter="IC")
    coordinator._session.get.return_value = _make_mock_response(SAMPLE_RESPONSE)

    data = await coordinator._async_update_data()

    assert data.line == "IC 123"


@pytest.mark.asyncio
async def test_line_filter_no_match_returns_neutral(hass):
    """line_filter='RE' should not match 'IC 123' — neutral state returned."""
    coordinator = _make_coordinator(hass, line_filter="RE")
    coordinator._session.get.return_value = _make_mock_response(SAMPLE_RESPONSE)

    data = await coordinator._async_update_data()

    # Neutral state: no departure found
    assert data.next_departure_dt is None
    assert data.minutes_until is None
    assert data.go_now is False


@pytest.mark.asyncio
async def test_line_filter_case_insensitive(hass):
    """line_filter is matched case-insensitively."""
    coordinator = _make_coordinator(hass, line_filter="ic")
    coordinator._session.get.return_value = _make_mock_response(SAMPLE_RESPONSE)

    data = await coordinator._async_update_data()

    assert data.line == "IC 123"


@pytest.mark.asyncio
async def test_go_now_true_when_within_walk_time(hass):
    """go_now is True when minutes_until <= walk_time_minutes."""
    from datetime import timezone as tz
    from homeassistant.util import dt as dt_util

    # Departure in 3 minutes from now
    now = dt_util.utcnow()
    departure_in_3 = (now + timedelta(minutes=3)).isoformat()
    payload = {
        "stop_id": STOP_ID,
        "stop_name": "Odense St.",
        "departures": [
            {
                "journey_id": "x",
                "stop_id": STOP_ID,
                "stop_name": "Odense St.",
                "line": "IC",
                "direction": "Aarhus",
                "planned_time": departure_in_3,
                "expected_time": departure_in_3,
                "delay_minutes": 0,
                "cancelled": False,
                "vehicle_type": "IC",
                "track": "1",
                "fetched_at": now.isoformat(),
            }
        ],
        "fetched_at": now.isoformat(),
    }

    coordinator = _make_coordinator(hass, walk_time_minutes=5)
    coordinator._session.get.return_value = _make_mock_response(payload)

    data = await coordinator._async_update_data()

    assert data.go_now is True
    assert data.minutes_until is not None
    assert data.minutes_until <= 5


@pytest.mark.asyncio
async def test_go_now_false_when_beyond_walk_time(hass):
    """go_now is False when minutes_until > walk_time_minutes."""
    from homeassistant.util import dt as dt_util

    now = dt_util.utcnow()
    departure_in_30 = (now + timedelta(minutes=30)).isoformat()
    payload = {
        "stop_id": STOP_ID,
        "stop_name": "Odense St.",
        "departures": [
            {
                "journey_id": "y",
                "stop_id": STOP_ID,
                "stop_name": "Odense St.",
                "line": "IC",
                "direction": "Aarhus",
                "planned_time": departure_in_30,
                "expected_time": departure_in_30,
                "delay_minutes": 0,
                "cancelled": False,
                "vehicle_type": "IC",
                "track": "1",
                "fetched_at": now.isoformat(),
            }
        ],
        "fetched_at": now.isoformat(),
    }

    coordinator = _make_coordinator(hass, walk_time_minutes=5)
    coordinator._session.get.return_value = _make_mock_response(payload)

    data = await coordinator._async_update_data()

    assert data.go_now is False


@pytest.mark.asyncio
async def test_go_now_false_when_cancelled(hass):
    """go_now is False even when minutes_until <= walk_time when departure is cancelled."""
    from homeassistant.util import dt as dt_util

    now = dt_util.utcnow()
    departure_in_2 = (now + timedelta(minutes=2)).isoformat()
    payload = {
        "stop_id": STOP_ID,
        "stop_name": "Odense St.",
        "departures": [
            {
                "journey_id": "z",
                "stop_id": STOP_ID,
                "stop_name": "Odense St.",
                "line": "IC",
                "direction": "Aarhus",
                "planned_time": departure_in_2,
                "expected_time": departure_in_2,
                "delay_minutes": 0,
                "cancelled": True,
                "vehicle_type": "IC",
                "track": "1",
                "fetched_at": now.isoformat(),
            }
        ],
        "fetched_at": now.isoformat(),
    }

    coordinator = _make_coordinator(hass, walk_time_minutes=5)
    coordinator._session.get.return_value = _make_mock_response(payload)

    data = await coordinator._async_update_data()

    assert data.go_now is False
    assert data.cancelled is True


@pytest.mark.asyncio
async def test_api_returns_http_error_raises_update_failed(hass):
    """HTTP 500 from the API raises UpdateFailed."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    coordinator = _make_coordinator(hass)
    coordinator._session.get.return_value = _make_mock_response({}, status=500)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_empty_departures_returns_neutral(hass):
    """Empty departures list returns neutral state without raising."""
    coordinator = _make_coordinator(hass)
    coordinator._session.get.return_value = _make_mock_response(
        {"stop_id": STOP_ID, "stop_name": "Odense St.", "departures": [], "fetched_at": "2026-06-08T09:55:00+00:00"}
    )

    data = await coordinator._async_update_data()

    assert data.next_departure_dt is None
    assert data.go_now is False
    assert data.cancelled is False


@pytest.mark.asyncio
async def test_delay_minutes_computed_from_timestamps(hass):
    """delay_minutes is computed from planned vs expected time difference."""
    from homeassistant.util import dt as dt_util

    now = dt_util.utcnow()
    planned = (now + timedelta(minutes=10)).isoformat()
    expected = (now + timedelta(minutes=15)).isoformat()  # 5 min late
    payload = {
        "stop_id": STOP_ID,
        "stop_name": "Odense St.",
        "departures": [
            {
                "journey_id": "d1",
                "stop_id": STOP_ID,
                "stop_name": "Odense St.",
                "line": "IC",
                "direction": "Aarhus",
                "planned_time": planned,
                "expected_time": expected,
                "delay_minutes": 5,
                "cancelled": False,
                "vehicle_type": "IC",
                "track": "2",
                "fetched_at": now.isoformat(),
            }
        ],
        "fetched_at": now.isoformat(),
    }

    coordinator = _make_coordinator(hass)
    coordinator._session.get.return_value = _make_mock_response(payload)

    data = await coordinator._async_update_data()

    assert data.delay_minutes == 5
