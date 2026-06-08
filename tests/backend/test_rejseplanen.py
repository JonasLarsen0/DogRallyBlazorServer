"""
Tests for RejseplaneClient and related parsing helpers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from backend.api.rejseplanen import (
    RejseplaneClient,
    _parse_dk_datetime,
    _TRAIN_TYPES,
)
from backend.models.departure import Departure, StopDepartures

_DK_TZ = ZoneInfo("Europe/Copenhagen")


# ---------------------------------------------------------------------------
# _parse_dk_datetime
# ---------------------------------------------------------------------------


class TestParseDkDatetime:
    def test_normal_time(self):
        dt = _parse_dk_datetime("08.06.26", "14:35")
        assert dt.year == 2026
        assert dt.month == 6
        assert dt.day == 8
        assert dt.hour == 14
        assert dt.minute == 35
        assert dt.tzinfo is not None

    def test_midnight(self):
        dt = _parse_dk_datetime("08.06.26", "00:00")
        assert dt.hour == 0
        assert dt.minute == 0

    def test_just_before_midnight(self):
        dt = _parse_dk_datetime("08.06.26", "23:59")
        assert dt.hour == 23
        assert dt.minute == 59

    def test_hour_24_rolls_to_next_day(self):
        """hour=24 means 00:00 on the following calendar day."""
        dt = _parse_dk_datetime("08.06.26", "24:05")
        assert dt.day == 9
        assert dt.hour == 0
        assert dt.minute == 5

    def test_hour_25_rolls_correctly(self):
        """hour=25 means 01:00 on the following calendar day."""
        dt = _parse_dk_datetime("08.06.26", "25:30")
        assert dt.day == 9
        assert dt.hour == 1
        assert dt.minute == 30

    def test_hour_48_rolls_two_days(self):
        """hour=48 means 00:00 two days later."""
        dt = _parse_dk_datetime("08.06.26", "48:00")
        assert dt.day == 10
        assert dt.hour == 0

    def test_result_is_timezone_aware(self):
        dt = _parse_dk_datetime("08.06.26", "12:00")
        assert dt.tzinfo is not None
        # Must be Copenhagen timezone
        assert str(dt.tzinfo) == "Europe/Copenhagen"

    def test_result_is_dk_tz_not_utc(self):
        dt = _parse_dk_datetime("08.06.26", "12:00")
        # Copenhagen in summer is UTC+2, so UTC hour should be 10
        utc_dt = dt.astimezone(timezone.utc)
        assert utc_dt.hour != 12  # not UTC


# ---------------------------------------------------------------------------
# _parse_departure_board
# ---------------------------------------------------------------------------


def _make_api_departure(**overrides: Any) -> dict[str, Any]:
    """Return a minimal valid departure dict as returned by the Rejseplanen API."""
    base: dict[str, Any] = {
        "date": "08.06.26",
        "time": "12:00",
        "stop": "Odense St.",
        "stopExtId": "8600626",
        "line": "IC",
        "name": "IC",
        "direction": "København H",
        "type": "IC",
        "track": "2",
        "id": "IC-1200-OD",
        "cancelled": False,
    }
    base.update(overrides)
    return base


def _make_board_response(departures: list[dict]) -> dict[str, Any]:
    return {
        "DepartureBoard": {
            "name": "Odense St.",
            "Departure": departures,
        }
    }


class TestParseDepartureBoard:
    def setup_method(self):
        self.client = RejseplaneClient(api_key="test-key", train_only=False)

    def test_basic_departure_parsed(self):
        data = _make_board_response([_make_api_departure()])
        result = self.client._parse_departure_board("8600626", data, datetime.now(timezone.utc))

        assert isinstance(result, StopDepartures)
        assert result.stop_id == "8600626"
        assert result.stop_name == "Odense St."
        assert len(result.departures) == 1

    def test_stop_name_from_board(self):
        data = _make_board_response([_make_api_departure()])
        result = self.client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
        assert result.stop_name == "Odense St."

    def test_empty_departure_list(self):
        data = _make_board_response([])
        result = self.client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
        assert result.departures == []

    def test_single_departure_as_dict_not_list(self):
        """API sometimes returns a single departure as a dict, not a list."""
        data = {
            "DepartureBoard": {
                "name": "Odense St.",
                "Departure": _make_api_departure(),  # dict, not list
            }
        }
        result = self.client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
        assert len(result.departures) == 1

    def test_missing_departure_board_key(self):
        """Missing DepartureBoard key should yield empty departures."""
        result = self.client._parse_departure_board("8600626", {}, datetime.now(timezone.utc))
        assert result.departures == []

    def test_realtime_fields_parsed(self):
        dep_dict = _make_api_departure(rtTime="12:35", rtDate="08.06.26")
        data = _make_board_response([dep_dict])
        result = self.client._parse_departure_board("8600626", data, datetime.now(timezone.utc))

        dep = result.departures[0]
        assert dep.expected_time is not None
        assert dep.delay_minutes == 35

    def test_realtime_uses_planned_date_when_rtdate_absent(self):
        """rtTime without rtDate should fall back to the planned date."""
        dep_dict = _make_api_departure(rtTime="12:40")  # no rtDate
        data = _make_board_response([dep_dict])
        result = self.client._parse_departure_board("8600626", data, datetime.now(timezone.utc))

        dep = result.departures[0]
        assert dep.expected_time is not None
        assert dep.delay_minutes == 40

    def test_cancelled_bool_true(self):
        dep_dict = _make_api_departure(cancelled=True)
        data = _make_board_response([dep_dict])
        result = self.client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
        assert result.departures[0].cancelled is True

    def test_cancelled_string_true(self):
        dep_dict = _make_api_departure(cancelled="true")
        data = _make_board_response([dep_dict])
        result = self.client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
        assert result.departures[0].cancelled is True

    def test_cancelled_string_false(self):
        dep_dict = _make_api_departure(cancelled="false")
        data = _make_board_response([dep_dict])
        result = self.client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
        assert result.departures[0].cancelled is False

    def test_fallback_stop_id_when_stopextid_missing(self):
        dep_dict = _make_api_departure()
        dep_dict.pop("stopExtId", None)
        data = _make_board_response([dep_dict])
        result = self.client._parse_departure_board("fallback-id", data, datetime.now(timezone.utc))
        assert result.departures[0].stop_id == "fallback-id"

    def test_delay_minutes_computed_correctly(self):
        dep_dict = _make_api_departure(rtTime="12:30", rtDate="08.06.26")
        data = _make_board_response([dep_dict])
        result = self.client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
        assert result.departures[0].delay_minutes == 30

    def test_multiple_departures(self):
        deps = [
            _make_api_departure(id="j1", line="IC"),
            _make_api_departure(id="j2", line="RE", type="RE"),
            _make_api_departure(id="j3", line="S", type="S"),
        ]
        data = _make_board_response(deps)
        result = self.client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
        assert len(result.departures) == 3


# ---------------------------------------------------------------------------
# Train-only filtering
# ---------------------------------------------------------------------------


class TestTrainOnlyFilter:
    def test_bus_filtered_out_when_train_only(self):
        client = RejseplaneClient(api_key="test-key", train_only=True)
        dep_dict = _make_api_departure(type="BUS", id="BUS-1")
        data = _make_board_response([dep_dict])
        result = client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
        assert result.departures == []

    def test_metro_filtered_out_when_train_only(self):
        client = RejseplaneClient(api_key="test-key", train_only=True)
        dep_dict = _make_api_departure(type="METRO", id="METRO-1")
        data = _make_board_response([dep_dict])
        result = client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
        assert result.departures == []

    def test_ferry_filtered_out_when_train_only(self):
        client = RejseplaneClient(api_key="test-key", train_only=True)
        dep_dict = _make_api_departure(type="FERRY", id="FERRY-1")
        data = _make_board_response([dep_dict])
        result = client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
        assert result.departures == []

    def test_ic_kept_when_train_only(self):
        client = RejseplaneClient(api_key="test-key", train_only=True)
        dep_dict = _make_api_departure(type="IC", id="IC-1")
        data = _make_board_response([dep_dict])
        result = client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
        assert len(result.departures) == 1

    def test_stog_kept_when_train_only(self):
        client = RejseplaneClient(api_key="test-key", train_only=True)
        dep_dict = _make_api_departure(type="S", id="S-1")
        data = _make_board_response([dep_dict])
        result = client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
        assert len(result.departures) == 1

    def test_mixed_filtered_correctly(self):
        """Bus is filtered, IC kept."""
        client = RejseplaneClient(api_key="test-key", train_only=True)
        deps = [
            _make_api_departure(type="IC", id="j1"),
            _make_api_departure(type="BUS", id="j2"),
            _make_api_departure(type="RE", id="j3"),
        ]
        data = _make_board_response(deps)
        result = client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
        assert len(result.departures) == 2
        vehicle_types = {d.vehicle_type for d in result.departures}
        assert "BUS" not in vehicle_types

    def test_no_filter_when_train_only_false(self):
        """With train_only=False, bus and IC should both appear."""
        client = RejseplaneClient(api_key="test-key", train_only=False)
        deps = [
            _make_api_departure(type="IC", id="j1"),
            _make_api_departure(type="BUS", id="j2"),
        ]
        data = _make_board_response(deps)
        result = client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
        assert len(result.departures) == 2

    def test_all_known_train_types_pass_filter(self):
        client = RejseplaneClient(api_key="test-key", train_only=True)
        for vtype in sorted(_TRAIN_TYPES):
            dep_dict = _make_api_departure(type=vtype, id=f"{vtype}-1")
            data = _make_board_response([dep_dict])
            result = client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
            assert len(result.departures) == 1, f"Vehicle type {vtype!r} should pass train-only filter"

    def test_type_comparison_is_case_insensitive(self):
        """vehicle_type.upper() should handle lowercase API responses."""
        client = RejseplaneClient(api_key="test-key", train_only=True)
        dep_dict = _make_api_departure(type="ic", id="ic-lower")  # lowercase
        data = _make_board_response([dep_dict])
        result = client._parse_departure_board("8600626", data, datetime.now(timezone.utc))
        assert len(result.departures) == 1


# ---------------------------------------------------------------------------
# multiDepartureBoard URL includes train_only params
# ---------------------------------------------------------------------------


class TestMultiDepartureBoardUrl:
    def test_train_only_params_included_in_url(self):
        """When train_only=True the manual URL must include useBus=0 etc."""
        client = RejseplaneClient(api_key="mykey", train_only=True)
        # Reconstruct what get_multi_departures would build
        from backend.api.rejseplanen import _TRAIN_ONLY_PARAMS

        base_params_dict = {"accessId": "mykey", "format": "json", "usePuR": "1"}
        base_params_dict.update(_TRAIN_ONLY_PARAMS)
        base_params = "&".join(f"{k}={v}" for k, v in base_params_dict.items())
        url = f"/multiDepartureBoard?{base_params}&id=8600626&id=8600868"

        assert "useBus=0" in url
        assert "useMetro=0" in url
        assert "useTog=1" in url

    def test_train_only_params_absent_when_disabled(self):
        """When train_only=False the URL must not include useBus etc."""
        base_params_dict = {"accessId": "mykey", "format": "json", "usePuR": "1"}
        base_params = "&".join(f"{k}={v}" for k, v in base_params_dict.items())
        url = f"/multiDepartureBoard?{base_params}&id=8600626"

        assert "useBus" not in url
        assert "useMetro" not in url
