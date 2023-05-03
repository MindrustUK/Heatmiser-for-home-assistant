# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""Config flow for Heatmiser Neo."""

import socket
import voluptuous as vol

from copy import deepcopy
from typing import Dict
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get,
)
from homeassistant import config_entries, core, exceptions
import homeassistant.helpers.config_validation as cv

import logging

from homeassistant.const import (
    CONF_HOST,
    CONF_PORT
)

from homeassistant.components.climate.const import (
    HVAC_MODE_COOL,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL
)

from .const import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DOMAIN,
    CONF_HVAC_MODES,
    AvailableMode
)

from homeassistant.core import callback
from homeassistant.helpers.typing import DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

modes = {
    AvailableMode.HEAT: 'Heat', 
    AvailableMode.COOL: 'Cool', 
    AvailableMode.AUTO: 'Heat/Cool', 
    AvailableMode.VENT: 'Fan'
}
default_modes = [HVAC_MODE_HEAT]

@config_entries.HANDLERS.register("heatmiserneo")
class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize Heatmiser Neo options flow."""
        self._host = DEFAULT_HOST
        self._port = DEFAULT_PORT
        self._errors = None

    async def async_step_zeroconf(self, discovery_info: DiscoveryInfoType):
        """Handle zeroconf discovery."""
        _LOGGER.debug("Zeroconfig discovered %s" % discovery_info)
        self._host = discovery_info['hostname']

        await self.async_set_unique_id(f"{self._host}:{self._port}")
        self._abort_if_unique_id_configured()
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(self, user_input=None):
        _LOGGER.debug(f"context {self.context}")
        """Handle a flow initiated by zeroconf."""
        if user_input is not None:
            self._errors = await self.try_connection()
            if not self._errors:
                return self._async_get_entry()
            return await self.async_step_user()

        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                'name': self._host
            },
        )

    async def try_connection(self):
        _LOGGER.debug("Trying connection...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            sock.connect((self._host, self._port))
        except OSError:
            return "cannot_connect"
        sock.close()
        _LOGGER.debug("Connection Worked!")
        return None

    @callback
    def _async_get_entry(self):
        return self.async_create_entry(
            title=f"{self._host}:{self._port}", 
            data={
                CONF_HOST: self._host,
                CONF_PORT: self._port
            }
        )
    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        _LOGGER.debug(f"User Input {user_input}")
        errors = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._port = user_input[CONF_PORT]

            await self.async_set_unique_id(f"{self._host}:{self._port}")
            self._abort_if_unique_id_configured()

            self._errors = await self.try_connection()
            if not self._errors:
                return self._async_get_entry()

            _LOGGER.error(f"Error: {self._errors}")

        return self.async_show_form(
            step_id="user", 
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self._host): str,
                    vol.Required(CONF_PORT, default=self._port): int
                }
            ), 
            errors=self._errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""
    
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self.config = deepcopy(config_entry.options[CONF_HVAC_MODES]) if CONF_HVAC_MODES in self.config_entry.options else {}

    async def async_step_init(self, user_input: Dict[str, str] = None) -> Dict[str, str]:
        """Manage the options for the custom component."""
        errors: Dict[str, str] = {}
        
        # Grab all devices from the entity registry so we can populate the
        # dropdown list that will allow a user to configure a device.
        entity_registry = await async_get(self.hass)
        devices = async_entries_for_config_entry(entity_registry, self.config_entry.entry_id)
        stats = {e.unique_id: e.capabilities for e in devices if e.entity_id.startswith('climate.')}

        if user_input is not None:
            _LOGGER.debug(f"user_input: {user_input}")
            _LOGGER.debug(f"original config: {self.config}")
            
            # Remove any devices where hvac_modes have been unset.
            remove_devices = [
                unique_id
                for unique_id in stats.keys()
                if unique_id == user_input["device"]
                if len(user_input["hvac_modes"]) == 0
            ]
            for unique_id in remove_devices:
                if unique_id in self.config:
                    self.config.pop(unique_id)

            if len(user_input["hvac_modes"]) != 0:
                if not errors:
                    # Add the new device config.
                    self.config[user_input["device"]] = user_input["hvac_modes"]
            
            _LOGGER.debug(f"updated config: {self.config}")

            if not errors:                
                # If user selected the 'more' tickbox, show this form again 
                # so they can configure additional devices.
                if user_input.get('more', False):
                    return await self.async_step_init()
                    
                # Value of data will be set on the options property of the config_entry instance.
                return self.async_create_entry(
                    title="",
                    data={CONF_HVAC_MODES: self.config}
                )
            
        options_schema = vol.Schema(
            {
                vol.Optional("device", default=list(stats.keys())): vol.In(stats.keys()),
                vol.Optional("hvac_modes", default=list(default_modes)): cv.multi_select(modes),
                vol.Optional("more"): cv.boolean
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )
