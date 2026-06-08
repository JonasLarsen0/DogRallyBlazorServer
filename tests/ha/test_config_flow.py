"""Tests for RejseplanAPI config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

DOMAIN = "rejseplan"

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

MOCK_STOPS = [
    {"id": "8600020", "name": "Odense St."},
    {"id": "8600021", "name": "Odense Banegård"},
]


def _mock_clientsession_success(status: int = 200):
    """Return a patched ClientSession whose GET always succeeds with *status*."""
    response = AsyncMock()
    response.status = status

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock(spec=aiohttp.ClientSession)
    session.get.return_value = cm
    return session


def _mock_clientsession_connection_error():
    """Return a patched ClientSession whose GET raises ClientConnectorError."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(
        side_effect=aiohttp.ClientConnectorError(MagicMock(), MagicMock())
    )
    cm.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock(spec=aiohttp.ClientSession)
    session.get.return_value = cm
    return session


def _mock_search_response(stops: list[dict]):
    """Return a ClientSession that returns a stop-search result."""
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value=stops)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock(spec=aiohttp.ClientSession)
    session.get.return_value = cm
    return session


# ---------------------------------------------------------------------------
# Step 1 — user (URL entry)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step_user_valid_url(hass):
    """A reachable URL advances to the search step."""
    with patch(
        "custom_components.rejseplan.config_flow.async_get_clientsession",
        return_value=_mock_clientsession_success(200),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"api_url": "http://localhost:8000"},
        )

    # Should advance to search step
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "search"


@pytest.mark.asyncio
async def test_step_user_connection_refused_shows_error(hass):
    """A connection error on URL validation shows the cannot_connect error."""
    with patch(
        "custom_components.rejseplan.config_flow.async_get_clientsession",
        return_value=_mock_clientsession_connection_error(),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"api_url": "http://unreachable:9999"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "user"
    assert result2["errors"]["base"] == "cannot_connect"


@pytest.mark.asyncio
async def test_step_user_404_is_treated_as_success(hass):
    """A 404 response (server up, endpoint not found) is still treated as reachable."""
    with patch(
        "custom_components.rejseplan.config_flow.async_get_clientsession",
        return_value=_mock_clientsession_success(404),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"api_url": "http://localhost:8000"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "search"


# ---------------------------------------------------------------------------
# Step 2 — search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step_search_empty_query_shows_error(hass):
    """An empty search query shows a validation error."""
    with patch(
        "custom_components.rejseplan.config_flow.async_get_clientsession",
        return_value=_mock_clientsession_success(200),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"api_url": "http://localhost:8000"},
        )

    # Now at search step — submit empty query
    with patch(
        "custom_components.rejseplan.config_flow.async_get_clientsession",
        return_value=_mock_search_response([]),
    ):
        search_result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"search_query": ""},
        )

    assert search_result["type"] == FlowResultType.FORM
    assert search_result["step_id"] == "search"
    assert "search_query" in search_result["errors"]


@pytest.mark.asyncio
async def test_step_search_no_results_shows_error(hass):
    """When the API returns no stops, a no_stops_found error is shown."""
    with patch(
        "custom_components.rejseplan.config_flow.async_get_clientsession",
        return_value=_mock_clientsession_success(200),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"api_url": "http://localhost:8000"},
        )

    with patch(
        "custom_components.rejseplan.config_flow.async_get_clientsession",
        return_value=_mock_search_response([]),  # empty results
    ):
        search_result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"search_query": "nonexistentplace"},
        )

    assert search_result["type"] == FlowResultType.FORM
    assert search_result["step_id"] == "search"
    assert search_result["errors"]["base"] == "no_stops_found"


# ---------------------------------------------------------------------------
# Step 3 — configure_route + duplicate unique_id
# ---------------------------------------------------------------------------


async def _complete_flow(hass, stop_id: str = "8600020", line_filter: str = ""):
    """Helper: drive through all three steps and return the final FlowResult."""
    # Step 1
    with patch(
        "custom_components.rejseplan.config_flow.async_get_clientsession",
        return_value=_mock_clientsession_success(200),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"api_url": "http://localhost:8000"},
        )

    # Step 2
    with patch(
        "custom_components.rejseplan.config_flow.async_get_clientsession",
        return_value=_mock_search_response(MOCK_STOPS),
    ):
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"search_query": "Odense"},
        )

    # Step 3
    final = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "stop_id": stop_id,
            "line_filter": line_filter,
            "walk_time": 5,
        },
    )
    return final


@pytest.mark.asyncio
async def test_full_flow_creates_entry(hass):
    """A complete three-step flow creates a config entry."""
    result = await _complete_flow(hass)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["stop_id"] == "8600020"
    assert result["data"]["api_url"] == "http://localhost:8000"
    assert result["data"]["walk_time"] == 5


@pytest.mark.asyncio
async def test_duplicate_stop_aborts(hass):
    """Configuring the same stop/line combination twice aborts with already_configured."""
    # First flow — succeeds
    await _complete_flow(hass, stop_id="8600020", line_filter="")

    # Second flow — same unique_id → should abort
    result = await _complete_flow(hass, stop_id="8600020", line_filter="")

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_different_line_filter_is_not_duplicate(hass):
    """Same stop with a different line filter is a distinct entry (not duplicate)."""
    await _complete_flow(hass, stop_id="8600020", line_filter="IC")
    result = await _complete_flow(hass, stop_id="8600020", line_filter="RE")

    assert result["type"] == FlowResultType.CREATE_ENTRY


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_options_flow_updates_walk_time(hass):
    """OptionsFlow allows updating walk_time."""
    # Create an entry first
    entry_result = await _complete_flow(hass)
    entry_id = entry_result["result"].entry_id

    # Open options flow
    result = await hass.config_entries.options.async_init(entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"walk_time": 10},
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"]["walk_time"] == 10
