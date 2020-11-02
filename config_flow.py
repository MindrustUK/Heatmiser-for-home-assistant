"""Config flow for Heatmiser Neo."""

import socket
import voluptuous as vol

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_NAME,
)

from .const import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DOMAIN,
)


SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)

@config_entries.HANDLERS.register("heatmiserneo")
class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize Heatmiser Neo options flow."""


    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""

        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)

            try:
                sock.connect((host, port))
            except OSError:
                errors["base"] = "cannot_connect"
            sock.close()

            if not errors:
                return self.async_create_entry(title=f"{host}:{port}", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=SCHEMA, errors=errors
        )
