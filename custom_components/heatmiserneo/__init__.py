# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

# Empty file for great migration new file structure

from homeassistant.const import (CONF_HOST,CONF_PORT)

from .heatmiserneo import NeoHub
from .const import (DOMAIN, HUB)

async def async_setup(hass, config):
    """Set up Heamiser Neo components."""
    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(hass, entry):
    """Set up Heatmiser Neo from a config entry."""

    hass.data[DOMAIN][entry.entry_id] = {
        CONF_HOST: entry.data[CONF_HOST],
        CONF_PORT: entry.data[CONF_PORT],
    }

    # Set the Hub up to use and save
    hass.data[DOMAIN][HUB] = NeoHub(hass.data[DOMAIN][CONF_HOST], hass.data[DOMAIN][CONF_PORT])

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "climate")
    )

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "switch")
    )

    return True
