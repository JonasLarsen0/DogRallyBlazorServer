"""The RejseplanAPI integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_URL,
    CONF_LINE_FILTER,
    CONF_STOP_ID,
    CONF_STOP_NAME,
    CONF_WALK_TIME,
    DEFAULT_WALK_TIME,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import RejseplanCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a RejseplanAPI config entry."""
    # Merge options on top of data so OptionsFlow updates take effect immediately
    api_url: str = entry.data[CONF_API_URL]
    stop_id: str = entry.data[CONF_STOP_ID]
    stop_name: str = entry.data.get(CONF_STOP_NAME, stop_id)
    line_filter: str = entry.data.get(CONF_LINE_FILTER, "")
    walk_time: int = int(
        entry.options.get(CONF_WALK_TIME, entry.data.get(CONF_WALK_TIME, DEFAULT_WALK_TIME))
    )

    session = async_get_clientsession(hass)

    coordinator = RejseplanCoordinator(
        hass=hass,
        api_url=api_url,
        stop_id=stop_id,
        stop_name=stop_name,
        line_filter=line_filter,
        walk_time_minutes=walk_time,
        session=session,
    )

    # Perform the first data fetch; raises ConfigEntryNotReady on failure
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Re-load when options are changed (walk_time slider in OptionsFlow)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options updates by reloading the config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
