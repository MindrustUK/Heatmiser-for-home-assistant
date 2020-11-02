# Empty file for great migration new file structure

from homeassistant.const import (CONF_HOST,CONF_PORT)

from .const import DOMAIN

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

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "climate")
    )

    return True
