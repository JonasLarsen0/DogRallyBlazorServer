"""
Shared pytest fixtures for backend tests.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

from backend.models.departure import Alert, Departure, StopDepartures

_DK_TZ = ZoneInfo("Europe/Copenhagen")
_UTC = timezone.utc


# ---------------------------------------------------------------------------
# Settings / config fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_settings(monkeypatch):
    """Return a Settings-like object with test-friendly defaults."""
    from backend import config as cfg

    monkeypatch.setattr(cfg.settings, "rejseplanen_api_key", "test-key-123")
    monkeypatch.setattr(cfg.settings, "poll_interval_seconds", 30)
    monkeypatch.setattr(cfg.settings, "train_only", False)
    monkeypatch.setattr(cfg.settings, "walk_time_seconds", 300)
    monkeypatch.setattr(cfg.settings, "default_stop_ids", "8600626,8600868")
    return cfg.settings


# ---------------------------------------------------------------------------
# Sample Departure objects
# ---------------------------------------------------------------------------


def _make_planned(hour: int = 12, minute: int = 0, day: int = 8) -> datetime:
    return datetime(2026, 6, day, hour, minute, tzinfo=_DK_TZ)


@pytest.fixture()
def departure_on_time() -> Departure:
    """A departure with no real-time data (on time)."""
    return Departure(
        stop_id="8600626",
        stop_name="Odense St.",
        line="IC",
        direction="København H",
        planned_time=_make_planned(12, 0),
        expected_time=None,
        cancelled=False,
        vehicle_type="IC",
        track="2",
        journey_id="IC-1200-OD",
    )


@pytest.fixture()
def departure_delayed_35() -> Departure:
    """A departure with a 35-minute delay."""
    planned = _make_planned(12, 0)
    expected = _make_planned(12, 35)
    return Departure(
        stop_id="8600626",
        stop_name="Odense St.",
        line="IC",
        direction="København H",
        planned_time=planned,
        expected_time=expected,
        cancelled=False,
        vehicle_type="IC",
        track="2",
        journey_id="IC-1235-OD",
    )


@pytest.fixture()
def departure_delayed_65() -> Departure:
    """A departure with a 65-minute delay."""
    planned = _make_planned(12, 0)
    expected = _make_planned(13, 5)
    return Departure(
        stop_id="8600626",
        stop_name="Odense St.",
        line="RE",
        direction="Esbjerg",
        planned_time=planned,
        expected_time=expected,
        cancelled=False,
        vehicle_type="RE",
        track="3",
        journey_id="RE-1305-OD",
    )


@pytest.fixture()
def departure_delayed_95() -> Departure:
    """A departure with a 95-minute delay (crosses all three tiers)."""
    planned = _make_planned(12, 0)
    expected = _make_planned(13, 35)
    return Departure(
        stop_id="8600626",
        stop_name="Odense St.",
        line="IC",
        direction="Aarhus H",
        planned_time=planned,
        expected_time=expected,
        cancelled=False,
        vehicle_type="IC",
        track="1",
        journey_id="IC-1335-OD",
    )


@pytest.fixture()
def departure_early() -> Departure:
    """A departure that arrives 5 minutes early (negative delay)."""
    planned = _make_planned(12, 0)
    expected = _make_planned(11, 55)
    return Departure(
        stop_id="8600626",
        stop_name="Odense St.",
        line="S",
        direction="Hellerup",
        planned_time=planned,
        expected_time=expected,
        cancelled=False,
        vehicle_type="S",
        track="4",
        journey_id="S-1155-OD",
    )


# ---------------------------------------------------------------------------
# Sample StopDepartures
# ---------------------------------------------------------------------------


@pytest.fixture()
def stop_departures_empty() -> StopDepartures:
    return StopDepartures(
        stop_id="8600626",
        stop_name="Odense St.",
        departures=[],
        fetched_at=datetime.now(_UTC),
    )


@pytest.fixture()
def stop_departures_mixed(
    departure_on_time,
    departure_delayed_35,
    departure_delayed_65,
) -> StopDepartures:
    return StopDepartures(
        stop_id="8600626",
        stop_name="Odense St.",
        departures=[departure_on_time, departure_delayed_35, departure_delayed_65],
        fetched_at=datetime.now(_UTC),
    )


# ---------------------------------------------------------------------------
# Mock RejseplaneClient
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_client() -> MagicMock:
    """A mock RejseplaneClient that returns empty results by default."""
    client = MagicMock()
    client.search_stops = AsyncMock(return_value=[])
    client.get_departures = AsyncMock(
        return_value=StopDepartures(
            stop_id="8600626",
            stop_name="Odense St.",
            departures=[],
            fetched_at=datetime.now(_UTC),
        )
    )
    client.get_multi_departures = AsyncMock(return_value=[])
    client.get_alerts = AsyncMock(return_value=[])
    client.aclose = AsyncMock()
    return client
