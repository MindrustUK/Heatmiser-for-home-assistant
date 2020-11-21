"""Config flow for Heatmiser Neo."""

import socket
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
import homeassistant.helpers.config_validation as cv

import logging

from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_NAME,
)

from .const import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DOMAIN,
    EXCLUDE_TIME_CLOCK,
)

from homeassistant.core import callback
from homeassistant.helpers.typing import DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)


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
        self._exclude_time_clock = False

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
                CONF_PORT: self._port,
                EXCLUDE_TIME_CLOCK: self._exclude_time_clock
            }
        )
    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        _LOGGER.debug(f"User Input {user_input}")
        errors = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._port = user_input[CONF_PORT]
            self._exclude_time_clock = user_input[EXCLUDE_TIME_CLOCK]

            await self.async_set_unique_id(f"{self._host}:{self._port}")
            self._abort_if_unique_id_configured()

            self._errors = await self.try_connection()
            if not self._errors:
                return self._async_get_entry()

        _LOGGER.debug(f"Error: {self._errors}")
        return self.async_show_form(
            step_id="user", 
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self._host): str,
                    vol.Required(CONF_PORT, default=self._port): int,
                    vol.Required(EXCLUDE_TIME_CLOCK, default=self._exclude_time_clock): bool
                }
            ), 
            errors=self._errors
        )
