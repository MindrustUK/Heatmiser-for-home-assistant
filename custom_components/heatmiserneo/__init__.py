# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
import logging
from datetime import timedelta
import async_timeout

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from homeassistant.const import CONF_HOST,CONF_PORT

from neohubapi.neohub import NeoHub
from .const import DOMAIN, HUB, COORDINATOR

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    """Set up Heamiser Neo components."""
    hass.data.setdefault(DOMAIN, {})

    return True

async def async_setup_entry(hass, entry):
    """Set up Heatmiser Neo from a config entry."""

    # Set the Hub up to use and save
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    hub = NeoHub(host, port)
    hass.data[DOMAIN][HUB] = hub

    async def async_update_data():
        """Fetch data from the Hub all at once and make it available for
           all devices.
        """
        _LOGGER.info(f"Executing update_data()")
        
        async with async_timeout.timeout(30):
            _, devices_data = await hub.get_live_data()
            system_data = await hub.get_system()
            
            #_LOGGER.debug(f"system_data: {system_data}")
            _LOGGER.debug(f"devices_data: {devices_data}")
            
            return (devices_data, system_data)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        # Name of the data. For logging purposes.
        name="neostat",
        update_method=async_update_data,
        # Polling interval. Will only be polled if there are subscribers.
        update_interval=timedelta(seconds=30)
    )

    hass.data[DOMAIN][COORDINATOR] = coordinator

    await coordinator.async_config_entry_first_refresh()
    
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "climate")
    )

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "switch")
    )

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return True
