"""
Tests for Pydantic models in backend.models.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from backend.models.departure import Departure, StopDepartures, Alert

_DK_TZ = ZoneInfo("Europe/Copenhagen")


def _make_departure(
    planned_hour: int = 12,
    planned_min: int = 0,
    expected_delta_minutes: int | None = None,
    journey_id: str = "test-journey",
) -> Departure:
    planned = datetime(2026, 6, 8, planned_hour, planned_min, tzinfo=_DK_TZ)
    expected: datetime | None = None
    if expected_delta_minutes is not None:
        expected = planned + timedelta(minutes=expected_delta_minutes)
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
        journey_id=journey_id,
    )


class TestDepartureDelayMinutes:
    def test_no_expected_time_returns_zero(self):
        dep = _make_departure(expected_delta_minutes=None)
        assert dep.delay_minutes == 0

    def test_on_time_expected_equals_planned(self):
        dep = _make_departure(expected_delta_minutes=0)
        assert dep.delay_minutes == 0

    def test_positive_delay(self):
        dep = _make_departure(expected_delta_minutes=35)
        assert dep.delay_minutes == 35

    def test_exactly_30_minutes_delay(self):
        dep = _make_departure(expected_delta_minutes=30)
        assert dep.delay_minutes == 30

    def test_exactly_60_minutes_delay(self):
        dep = _make_departure(expected_delta_minutes=60)
        assert dep.delay_minutes == 60

    def test_exactly_90_minutes_delay(self):
        dep = _make_departure(expected_delta_minutes=90)
        assert dep.delay_minutes == 90

    def test_large_delay_2_hours(self):
        dep = _make_departure(expected_delta_minutes=120)
        assert dep.delay_minutes == 120

    def test_early_arrival_negative_delay(self):
        """A train arriving early should return a negative delay_minutes."""
        dep = _make_departure(expected_delta_minutes=-5)
        assert dep.delay_minutes == -5

    def test_delay_minutes_is_integer(self):
        """delay_minutes must always be an int (truncated toward zero)."""
        dep = _make_departure(expected_delta_minutes=35)
        assert isinstance(dep.delay_minutes, int)

    def test_partial_minute_truncated(self):
        """Sub-minute deltas should be truncated, not rounded."""
        planned = datetime(2026, 6, 8, 12, 0, 0, tzinfo=_DK_TZ)
        # 35 min 59 sec → still 35 min when int-truncated
        expected = planned + timedelta(minutes=35, seconds=59)
        dep = Departure(
            stop_id="8600626",
            stop_name="Odense St.",
            line="IC",
            direction="København H",
            planned_time=planned,
            expected_time=expected,
            cancelled=False,
            vehicle_type="IC",
            journey_id="test-journey",
        )
        assert dep.delay_minutes == 35

    def test_delay_minutes_included_in_serialisation(self):
        """computed_field should appear in model_dump output."""
        dep = _make_departure(expected_delta_minutes=45)
        dumped = dep.model_dump()
        assert "delay_minutes" in dumped
        assert dumped["delay_minutes"] == 45


class TestDepartureDefaults:
    def test_track_defaults_to_none(self):
        """Omitting track should default to None."""
        dep = Departure(
            stop_id="8600626",
            stop_name="Odense St.",
            line="IC",
            direction="København H",
            planned_time=datetime(2026, 6, 8, 12, 0, tzinfo=_DK_TZ),
            cancelled=False,
            vehicle_type="IC",
            journey_id="test-journey",
            # track deliberately omitted
        )
        assert dep.track is None

    def test_expected_time_defaults_to_none(self):
        dep = _make_departure()
        assert dep.expected_time is None

    def test_cancelled_defaults_to_false(self):
        dep = _make_departure()
        assert dep.cancelled is False


class TestStopDepartures:
    def test_serialises_departures_list(self, stop_departures_mixed):
        data = stop_departures_mixed.model_dump(mode="json")
        assert "departures" in data
        assert len(data["departures"]) == 3

    def test_empty_departures(self, stop_departures_empty):
        assert stop_departures_empty.departures == []


class TestAlert:
    def test_defaults(self):
        alert = Alert(id="1", summary="Test disruption")
        assert alert.affected_lines == []
        assert alert.valid_from is None
        assert alert.valid_to is None
        assert alert.severity == "unknown"

    def test_full_alert(self):
        from datetime import timezone

        now = datetime.now(tz=timezone.utc)
        alert = Alert(
            id="42",
            summary="Line IC delayed",
            affected_lines=["IC", "RE"],
            valid_from=now,
            valid_to=now,
            severity="high",
        )
        assert alert.id == "42"
        assert len(alert.affected_lines) == 2
        assert alert.severity == "high"
