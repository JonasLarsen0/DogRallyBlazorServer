"""Config flow for RejseplanAPI integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    API_PATH_STOPS_SEARCH,
    CONF_API_URL,
    CONF_LINE_FILTER,
    CONF_STOP_ID,
    CONF_STOP_NAME,
    CONF_WALK_TIME,
    DEFAULT_WALK_TIME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_URL, default="http://localhost:8000"): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        ),
    }
)

STEP_SEARCH_SCHEMA = vol.Schema(
    {
        vol.Required("search_query"): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        ),
    }
)


def _slugify(text: str) -> str:
    """Return a lowercase, underscore-separated version of *text*."""
    import re
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


async def _validate_api_url(session: aiohttp.ClientSession, api_url: str) -> str | None:
    """
    Try to reach the API.  Returns an error key string on failure, None on success.
    We hit /api/departures/<known-dummy> and accept any HTTP response (even 404)
    as proof that the server is reachable; a connection error is the real failure.
    """
    url = api_url.rstrip("/") + "/api/departures/0"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            # Any HTTP response (200, 404, 422 …) means the server is up
            _ = resp.status
    except aiohttp.InvalidURL:
        return "invalid_url"
    except aiohttp.ClientConnectorError:
        return "cannot_connect"
    except aiohttp.ClientError:
        return "cannot_connect"
    except Exception:  # noqa: BLE001
        return "unknown"
    return None


async def _search_stops(
    session: aiohttp.ClientSession, api_url: str, query: str
) -> list[dict[str, str]]:
    """
    Call GET /api/stops/search?q=<query> and return a list of
    {"id": "...", "name": "..."} dicts.  Returns [] on any error.
    """
    url = api_url.rstrip("/") + API_PATH_STOPS_SEARCH
    try:
        async with session.get(
            url, params={"q": query}, timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            # Accept both a list of dicts and a dict with a "results" / "stops" key
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("results", data.get("stops", []))
    except aiohttp.ClientError as err:
        _LOGGER.warning("Stop search failed: %s", err)
    return []


class RejseplanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Multi-step config flow for RejseplanAPI."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise flow state."""
        self._api_url: str = ""
        self._stop_results: list[dict[str, str]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1 — collect and validate the API base URL."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_url = user_input[CONF_API_URL].rstrip("/")
            session = async_get_clientsession(self.hass)
            error_key = await _validate_api_url(session, api_url)
            if error_key:
                errors["base"] = error_key
            else:
                self._api_url = api_url
                return await self.async_step_search()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"default_url": "http://localhost:8000"},
        )

    async def async_step_search(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2 — search for stops by free-text query."""
        errors: dict[str, str] = {}

        if user_input is not None:
            query = user_input.get("search_query", "").strip()
            if not query:
                errors["search_query"] = "search_query_empty"
            else:
                session = async_get_clientsession(self.hass)
                self._stop_results = await _search_stops(session, self._api_url, query)
                if not self._stop_results:
                    errors["base"] = "no_stops_found"
                else:
                    return await self.async_step_configure_route()

        return self.async_show_form(
            step_id="search",
            data_schema=STEP_SEARCH_SCHEMA,
            errors=errors,
        )

    async def async_step_configure_route(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3 — pick stop, optional line filter, walk time."""
        errors: dict[str, str] = {}

        stop_options = [
            SelectOptionDict(
                value=str(stop.get("id", stop.get("stop_id", ""))),
                label=stop.get("name", stop.get("stop_name", str(stop.get("id", "")))),
            )
            for stop in self._stop_results
            if stop.get("id") or stop.get("stop_id")
        ]

        schema = vol.Schema(
            {
                vol.Required(CONF_STOP_ID): SelectSelector(
                    SelectSelectorConfig(
                        options=stop_options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_LINE_FILTER, default=""): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.TEXT)
                ),
                vol.Optional(CONF_WALK_TIME, default=DEFAULT_WALK_TIME): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=30,
                        step=1,
                        unit_of_measurement="min",
                        mode=NumberSelectorMode.SLIDER,
                    )
                ),
            }
        )

        if user_input is not None:
            stop_id = str(user_input[CONF_STOP_ID])
            line_filter = (user_input.get(CONF_LINE_FILTER) or "").strip()
            walk_time = int(user_input.get(CONF_WALK_TIME, DEFAULT_WALK_TIME))

            # Resolve stop name from the search results
            stop_name = ""
            for stop in self._stop_results:
                sid = str(stop.get("id", stop.get("stop_id", "")))
                if sid == stop_id:
                    stop_name = stop.get("name", stop.get("stop_name", stop_id))
                    break

            unique_id = f"{stop_id}_{_slugify(line_filter)}" if line_filter else stop_id
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            title = f"{stop_name} {line_filter}".strip() if line_filter else stop_name

            return self.async_create_entry(
                title=title,
                data={
                    CONF_API_URL: self._api_url,
                    CONF_STOP_ID: stop_id,
                    CONF_STOP_NAME: stop_name,
                    CONF_LINE_FILTER: line_filter,
                    CONF_WALK_TIME: walk_time,
                },
            )

        return self.async_show_form(
            step_id="configure_route",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> RejseplanOptionsFlow:
        """Return the options flow handler."""
        return RejseplanOptionsFlow(config_entry)


class RejseplanOptionsFlow(config_entries.OptionsFlow):
    """Options flow — allows updating walk_time after initial setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialise with the current config entry."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the walk time option."""
        current_walk_time = self._config_entry.options.get(
            CONF_WALK_TIME,
            self._config_entry.data.get(CONF_WALK_TIME, DEFAULT_WALK_TIME),
        )

        schema = vol.Schema(
            {
                vol.Optional(CONF_WALK_TIME, default=int(current_walk_time)): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=30,
                        step=1,
                        unit_of_measurement="min",
                        mode=NumberSelectorMode.SLIDER,
                    )
                ),
            }
        )

        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={CONF_WALK_TIME: int(user_input[CONF_WALK_TIME])},
            )

        return self.async_show_form(step_id="init", data_schema=schema)
