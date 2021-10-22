# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

from homeassistant.const import CONF_HOST,CONF_PORT

from neohubapi.neohub import NeoHub
from .const import DOMAIN, HUB


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
