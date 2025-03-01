# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
"""The Heatmiser Neo integration."""

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from neohubapi.neohub import NeoHub
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN, CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .const import DISCOVER_SCAN_TIMEOUT, DISCOVERY_INTERVAL
from .coordinator import HeatmiserNeoCoordinator
from .discovery import (
    async_discover_device,
    async_discover_devices,
    async_trigger_discovery,
    async_update_entry_from_discovery,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.LOCK,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type HeatmiserNeoConfigEntry = ConfigEntry[HeatmiserNeoData]


@dataclass
class HeatmiserNeoData:
    """Class to store Heatmiser Neo runtime data."""

    hub: NeoHub
    coordinator: HeatmiserNeoCoordinator


async def async_setup(hass: HomeAssistant, hass_config: ConfigType) -> bool:
    """Set up the Heatmiser Neo integration."""

    async def _async_discovery(*_: Any) -> None:
        async_trigger_discovery(
            hass, await async_discover_devices(hass, DISCOVER_SCAN_TIMEOUT)
        )

    hass.async_create_background_task(
        _async_discovery(), "heatmiserneo setup discovery"
    )
    async_track_time_interval(
        hass, _async_discovery, DISCOVERY_INTERVAL, cancel_on_shutdown=True
    )
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatmiserNeoConfigEntry,
) -> bool:
    """Set up Heatmiser Neo from a config entry."""
    # Set the Hub up to use and save
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    token = entry.data.get(CONF_API_TOKEN)

    if not entry.unique_id or entry.unique_id.count(":") != 5:
        _LOGGER.debug(
            "Unique id for %s is missing during setup or it is not a MAC address, trying to fill from discovery",
            host,
        )
        if device := await async_discover_device(hass, host):
            async_update_entry_from_discovery(hass, entry, device)

    # Make this configurable or retrieve from an API later.
    hub_serial_number = f"NEOHUB-SN:000000-{host}"
    if token:
        hub = NeoHub(host, port, token=token)
    else:
        hub = NeoHub(host, port)

    coordinator = HeatmiserNeoCoordinator(hass, hub)

    coordinator.serial_number = hub_serial_number

    entry.runtime_data = HeatmiserNeoData(hub, coordinator)

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(
    hass: HomeAssistant, entry: HeatmiserNeoConfigEntry
) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: HeatmiserNeoConfigEntry
) -> bool:
    """Unload a config entry."""
    hub = entry.runtime_data.hub
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    await hub.disconnect()

    return unload_ok


async def options_update_listener(
    hass: HomeAssistant, config_entry: HeatmiserNeoConfigEntry
):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


def time_period_minutes(value: float | str) -> timedelta:
    """Validate and transform minutes to a time offset."""
    try:
        return timedelta(minutes=float(value))
    except (ValueError, TypeError) as err:
        raise vol.Invalid(f"Expected minutes, got {value}") from err


hold_duration_validation = vol.All(
    vol.Any(cv.time_period_str, time_period_minutes, timedelta, cv.time_period_dict),
    cv.positive_timedelta,
)
