# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""Config flow for Heatmiser Neo."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from copy import deepcopy
import logging
import socket
from typing import Any, Self

from neohubapi.discovery import NeoHubConnectDetails, NeoHubDetails
from neohubapi.neohub import NeoHub, NeoHubConnectionError
import voluptuous as vol

from homeassistant.components.climate import UnitOfTemperature
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_API_TOKEN, CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.network import is_ip_address
from homeassistant.helpers.selector import (
    DurationSelector,
    DurationSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.helpers.service_info.zeroconf import (
    ATTR_PROPERTIES_ID,
    ZeroconfServiceInfo,
)
from homeassistant.helpers.typing import DiscoveryInfoType

from .const import (
    CONF_CONN_METHOD_LEGACY,
    CONF_CONN_METHOD_WEBSOCKET,
    CONF_DEFAULTS,
    CONF_DISCOVERY_METHOD_AUTO_CONNECT,
    CONF_DISCOVERY_METHOD_HUBSEEK,
    CONF_DISCOVERY_METHOD_MANUAL,
    CONF_HVAC_MODES,
    CONF_PAIRING,
    CONF_PAIRING_REPEATER,
    CONF_STAT_HOLD_DURATION,
    CONF_STAT_HOLD_TEMP,
    CONF_STAT_MAX_TEMPERATURE,
    CONF_STAT_MIN_TEMPERATURE,
    CONF_THERMOSTAT_OPTIONS,
    CONF_TIMER_HOLD_DURATION,
    CONF_TIMER_OPTIONS,
    DEFAULT_HOST,
    DEFAULT_NEOSTAT_HOLD_DURATION,
    DEFAULT_NEOSTAT_MAX_TEMPERATURE,
    DEFAULT_NEOSTAT_MIN_TEMPERATURE,
    DEFAULT_NEOSTAT_TEMPERATURE_BOOST,
    DEFAULT_PORT,
    DEFAULT_TIMER_HOLD_DURATION,
    DEFAULT_WEBSOCKET_PORT,
    DISCOVER_AUTO_CONNECT_TIMEOUT,
    DISCOVER_SCAN_TIMEOUT,
    DOMAIN,
    HEATMISER_TEMPERATURE_UNIT_HA_UNIT,
    HEATMISER_TYPE_IDS_HC,
    AvailableMode,
    GlobalSystemType,
)
from .coordinator import HeatmiserNeoConfigEntry
from .discovery import (
    async_discover_device_connection_details,
    async_discover_devices,
    async_update_entry_from_discovery,
)
from .utils import hold_duration_validation

_LOGGER = logging.getLogger(__name__)


CONF_DEVICE = "device"


class FlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    auto_connect_task: asyncio.Task | None = None

    def __init__(self) -> None:
        """Initialize Heatmiser Neo options flow."""
        self.host = None
        self._port = None
        self._token = None
        self._discovered_device: NeoHubDetails | None = None
        self._discovered_devices: dict[str, NeoHubDetails] = {}

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery."""
        _LOGGER.debug("Zeroconfig discovered %s", discovery_info)

        self._discovered_device = NeoHubDetails(
            discovery_info.properties.get(ATTR_PROPERTIES_ID), discovery_info.host
        )
        _LOGGER.debug(
            "NeoHub discovered from zeroconf discovery: %s", self._discovered_device
        )
        return await self._async_handle_discovery()

    async def try_connection(self) -> tuple[str | None, str | None]:
        """Try connection to NeoHub."""
        _LOGGER.debug("Trying connection to NeoHub")
        mac_address: str | None = None
        try:
            hub = NeoHub(self.host, self._port, token=self._token)
            await hub.firmware()
            mac_address = str(hub.mac_address) if hub.mac_address else None
            await hub.disconnect()
        except NeoHubConnectionError:
            return None, "cannot_connect"
        _LOGGER.debug("Connection Worked!")
        return mac_address, None

    @callback
    def _async_get_entry(self) -> ConfigFlowResult:
        data = {CONF_HOST: self.host, CONF_PORT: self._port}
        if self._token:
            data[CONF_API_TOKEN] = self._token
        return self.async_create_entry(
            title=f"{self.host}:{self._port}",
            data=data,
        )

    async def _configure_entry(
        self, user_input: dict[str, Any]
    ) -> tuple[ConfigFlowResult | None, dict[str, str] | None]:
        errors = {}

        self.host = user_input[CONF_HOST]
        self._port = user_input[CONF_PORT]
        self._token = user_input.get(CONF_API_TOKEN)

        if self._discovered_device:
            await self.async_set_unique_id(
                dr.format_mac(self._discovered_device.mac_address),
                raise_on_progress=False,
            )
        else:
            await self.async_set_unique_id(f"{self.host}:{self._port}")
        self._abort_if_unique_id_configured(updates={CONF_HOST: self.host})

        mac_address, conn_error = await self.try_connection()
        if not conn_error:
            if mac_address:
                if not self._discovered_device:
                    _LOGGER.debug(
                        "Using MAC address %s from websocket connection as unique id",
                        mac_address,
                    )
                    await self.async_set_unique_id(
                        dr.format_mac(mac_address),
                        raise_on_progress=False,
                    )
                    self._abort_if_unique_id_configured(updates={CONF_HOST: self.host})
                elif dr.format_mac(mac_address) != dr.format_mac(
                    self._discovered_device.mac_address
                ):
                    return self.async_abort(
                        reason="connect_mismatch",
                        description_placeholders={
                            "mac_address_expected": dr.format_mac(
                                self._discovered_device.mac_address
                            ),
                            "ip_address_expected": self._discovered_device.ip_address,
                            "mac_address_connected": dr.format_mac(mac_address),
                            "ip_address_connected": self.host,
                        },
                    ), None

            for entry in self._async_current_entries(include_ignore=False):
                if _host_is_same(entry.data[CONF_HOST], self.host):
                    return self.async_abort(reason="already_configured"), None
            return self._async_get_entry(), None

        errors["base"] = conn_error
        return None, errors

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        return await self.async_step_choose_discovery_method()

    async def async_step_choose_discovery_method(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show menu to select websocket or legacy api."""
        return self.async_show_menu(
            step_id="choose_discovery_method",
            menu_options=[
                CONF_DISCOVERY_METHOD_AUTO_CONNECT,
                CONF_DISCOVERY_METHOD_HUBSEEK,
                CONF_DISCOVERY_METHOD_MANUAL,
            ],
        )

    async def async_step_discovery_method_auto_connect(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle connection using connect button on hub."""

        if not self.auto_connect_task:
            self.auto_connect_task = self.hass.async_create_task(
                async_discover_device_connection_details(self.hass)
            )

        if not self.auto_connect_task.done():
            return self.async_show_progress(
                progress_action="press_connect_button",
                progress_task=self.auto_connect_task,
                description_placeholders={
                    "timeout": str(DISCOVER_AUTO_CONNECT_TIMEOUT)
                },
            )

        connect_details = await self.auto_connect_task

        if connect_details and isinstance(connect_details, NeoHubConnectDetails):
            return self.async_show_progress_done(
                next_step_id=CONF_DISCOVERY_METHOD_AUTO_CONNECT + "_finish"
            )

        return self.async_show_progress_done(
            next_step_id=CONF_DISCOVERY_METHOD_AUTO_CONNECT + "_failed"
        )

    async def async_step_discovery_method_auto_connect_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle connection using connect button on hub."""
        assert self.auto_connect_task
        connect_details: NeoHubConnectDetails = await self.auto_connect_task
        self.auto_connect_task = None
        user_input = user_input if user_input else {}
        user_input[CONF_PORT] = DEFAULT_PORT
        ws_token = connect_details.direct_link_token
        if ws_token:
            user_input[CONF_API_TOKEN] = ws_token
            user_input[CONF_PORT] = DEFAULT_WEBSOCKET_PORT

        if CONF_HOST not in user_input:
            user_input[CONF_HOST] = connect_details.ip_address

        if not self._discovered_device:
            self._discovered_device = NeoHubDetails(
                mac_address=connect_details.mac_address,
                ip_address=connect_details.ip_address,
            )
        elif dr.format_mac(self._discovered_device.mac_address) != dr.format_mac(
            connect_details.mac_address
        ):
            return self.async_abort(
                reason="auto_connect_mismatch",
                description_placeholders={
                    "mac_address_expected": dr.format_mac(
                        self._discovered_device.mac_address
                    ),
                    "ip_address_expected": self._discovered_device.ip_address,
                    "mac_address_received": dr.format_mac(connect_details.mac_address),
                    "ip_address_received": connect_details.ip_address,
                },
            )

        if user_input:
            result, errors = await self._configure_entry(user_input)
            if not errors:
                assert result
                return result
        return self.async_abort(reason="auto_connect_timeout")

    async def async_step_discovery_method_auto_connect_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Abort auto connect failed."""
        self.auto_connect_task = None
        return self.async_abort(reason="auto_connect_timeout")

    async def async_step_discovery_method_hubseek(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            if mac := user_input[CONF_DEVICE]:
                await self.async_set_unique_id(mac, raise_on_progress=False)
                self._discovered_device = self._discovered_devices[mac]
            return await self.async_step_choose_conn_method()

        current_unique_ids = self._async_current_ids()
        current_hosts = {
            _resolve_ip_address(entry.data[CONF_HOST])
            for entry in self._async_current_entries(include_ignore=False)
        }
        discovered_devices = await async_discover_devices(
            self.hass, DISCOVER_SCAN_TIMEOUT
        )
        self._discovered_devices = {
            dr.format_mac(device.mac_address): device for device in discovered_devices
        }
        if not discovered_devices:
            return self.async_abort(reason="no_devices_discovered")
        devices_name: dict[str | None, str] = {
            mac: f"{device.mac_address} ({device.ip_address})"
            for mac, device in self._discovered_devices.items()
            if mac not in current_unique_ids and device.ip_address not in current_hosts
        }
        if not devices_name:
            return self.async_abort(reason="no_new_devices_discovered")
        return self.async_show_form(
            step_id=CONF_DISCOVERY_METHOD_HUBSEEK,
            data_schema=vol.Schema({vol.Required(CONF_DEVICE): vol.In(devices_name)}),
        )

    async def async_step_discovery_method_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        return await self.async_step_choose_conn_method(
            user_input={CONF_DISCOVERY_METHOD_AUTO_CONNECT: False}
        )

    async def async_step_choose_conn_method(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show menu to select websocket or legacy api."""
        menu_options = [
            CONF_CONN_METHOD_WEBSOCKET,
            CONF_CONN_METHOD_LEGACY,
        ]
        if not user_input or user_input.get(CONF_DISCOVERY_METHOD_AUTO_CONNECT):
            menu_options.insert(0, CONF_DISCOVERY_METHOD_AUTO_CONNECT)
        return self.async_show_menu(
            step_id="choose_conn_method",
            menu_options=menu_options,
        )

    async def async_step_conn_method_websocket(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle connection to websocket api."""

        errors = {}
        if user_input is not None:
            user_input[CONF_PORT] = DEFAULT_WEBSOCKET_PORT
            result, errors = await self._configure_entry(user_input)
            if not errors:
                assert result
                return result
        return self.async_show_form(
            step_id=CONF_CONN_METHOD_WEBSOCKET,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=self._discovered_device.ip_address
                        if self._discovered_device
                        else self.host
                        if self.host
                        else DEFAULT_HOST,
                    ): str,
                    vol.Required(CONF_API_TOKEN, default=self._token): str,
                }
            ),
            errors=errors,
        )

    async def async_step_conn_method_legacy(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle connection to legacy api."""
        errors = {}

        if self._discovered_device:
            user_input = user_input if user_input else {}
            user_input[CONF_HOST] = self._discovered_device.ip_address
            user_input[CONF_PORT] = DEFAULT_PORT
            result, errors = await self._configure_entry(user_input)
            if not errors:
                assert result
                return result
        elif user_input is not None:
            user_input[CONF_PORT] = DEFAULT_PORT
            result, errors = await self._configure_entry(user_input)
            if not errors:
                assert result
                return result

        return self.async_show_form(
            step_id=CONF_CONN_METHOD_LEGACY,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=self._discovered_device.ip_address
                        if self._discovered_device
                        else self.host
                        if self.host
                        else DEFAULT_HOST,
                    ): str
                }
            ),
            errors=errors,
        )

    async def async_step_integration_discovery(
        self, discovery_info: DiscoveryInfoType
    ) -> ConfigFlowResult:
        """Handle integration discovery."""
        self._discovered_device = NeoHubDetails(
            discovery_info["mac_address"], discovery_info["ip_address"]
        )
        _LOGGER.debug(
            "NeoHub discovered from integration discovery: %s", self._discovered_device
        )
        return await self._async_handle_discovery()

    async def _async_handle_discovery(self) -> ConfigFlowResult:
        """Handle any discovery."""
        device = self._discovered_device
        assert device is not None
        mac = dr.format_mac(device.mac_address)
        host = device.ip_address
        await self.async_set_unique_id(mac)
        for entry in self._async_current_entries(include_ignore=False):
            if entry.unique_id == mac or _host_is_same(entry.data[CONF_HOST], host):
                if async_update_entry_from_discovery(self.hass, entry, device):
                    self.hass.config_entries.async_schedule_reload(entry.entry_id)
                return self.async_abort(reason="already_configured")
        self.host = host
        if self.hass.config_entries.flow.async_has_matching_flow(self):
            return self.async_abort(reason="already_in_progress")
        # Handled ignored case since _async_current_entries
        # is called with include_ignore=False
        self._abort_if_unique_id_configured(updates={CONF_HOST: self.host})
        return await self.async_step_choose_conn_method()

    def is_matching(self, other_flow: Self) -> bool:
        """Return True if other_flow is matching this flow."""
        return other_flow.host == self.host

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


def _resolve_ip_address(host: str) -> str:
    """Check if host1 and host2 are the same."""
    host = host.split(":")[0]
    return host if is_ip_address(host) else socket.gethostbyname(host)


def _host_is_same(host1: str, host2: str) -> bool:
    """Check if host1 and host2 are the same."""
    return _resolve_ip_address(host1) == _resolve_ip_address(host2)


class OptionsFlowHandler(OptionsFlow):
    """Handles options flow for the component."""

    _progress_task: asyncio.Task | None = None

    def __init__(self, config_entry: HeatmiserNeoConfigEntry) -> None:
        """Initialize options flow."""
        self._hvac_config = deepcopy(config_entry.options.get(CONF_HVAC_MODES, {}))
        self._defaults_config = deepcopy(
            config_entry.options.get(
                CONF_DEFAULTS,
                {
                    CONF_STAT_HOLD_DURATION: {"minutes": DEFAULT_NEOSTAT_HOLD_DURATION},
                    CONF_STAT_MAX_TEMPERATURE: DEFAULT_NEOSTAT_MAX_TEMPERATURE,
                    CONF_STAT_MIN_TEMPERATURE: DEFAULT_NEOSTAT_MIN_TEMPERATURE,
                    CONF_STAT_HOLD_TEMP: DEFAULT_NEOSTAT_TEMPERATURE_BOOST,
                    CONF_TIMER_HOLD_DURATION: {"minutes": DEFAULT_TIMER_HOLD_DURATION},
                },
            )
        )

        self._devices, _ = config_entry.runtime_data.coordinator.data
        self._new_devices = None
        system_data = config_entry.runtime_data.coordinator.system_data

        self.neostat_hcs = sorted(
            [
                k
                for k, v in self._devices.items()
                if v.device_type in HEATMISER_TYPE_IDS_HC and not v.time_clock_mode
            ]
        )

        mandatory_modes = []
        system_modes = []
        if system_data.GLOBAL_SYSTEM_TYPE == GlobalSystemType.HEAT_ONLY:
            mandatory_modes.append(AvailableMode.HEAT)
        elif system_data.GLOBAL_SYSTEM_TYPE == GlobalSystemType.COOL_ONLY:
            mandatory_modes.append(AvailableMode.COOL)
        else:
            system_modes.append(AvailableMode.HEAT)
            system_modes.append(AvailableMode.COOL)
            system_modes.append(AvailableMode.AUTO)
        system_modes.append(AvailableMode.VENT)

        self._system_modes = {k.value for k in system_modes}
        self._mandatory_modes = {k.value for k in mandatory_modes}
        self._unit_of_measurement = HEATMISER_TEMPERATURE_UNIT_HA_UNIT.get(
            system_data.CORF, UnitOfTemperature.CELSIUS
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the flow initiated by the user."""
        return await self.async_step_choose_options(user_input=user_input)

    async def async_step_choose_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle local vs cloud mode selection step."""

        menu_options = {
            CONF_DEFAULTS: "Configure default settings for devices",
            CONF_HVAC_MODES: "Configure HVAC modes for NeoStatHC",
            "choose_advanced": "Advanced options",
        }

        if len(self.neostat_hcs) == 0:
            del menu_options[CONF_HVAC_MODES]

        return self.async_show_menu(
            step_id="choose_options",
            menu_options=menu_options,
        )

    async def async_step_hvac_modes(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options for the custom component."""
        errors: dict[str, str] = {}

        if user_input is not None:
            _LOGGER.debug("user_input: %s", user_input)
            _LOGGER.debug("original config: %s", self._hvac_config)

            # Remove any devices where hvac_modes have been unset.
            for d in self.neostat_hcs:
                modes = set(user_input.get(d, []))
                if len(modes) == len(self._system_modes):
                    if d in self._hvac_config:
                        del self._hvac_config[d]
                elif not errors:
                    self._hvac_config[d] = sorted(modes.union(self._mandatory_modes))

            _LOGGER.debug("updated config: %s", self._hvac_config)

            if not errors:
                # Value of data will be set on the options property of the config_entry instance.
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_HVAC_MODES: self._hvac_config,
                        CONF_DEFAULTS: self._defaults_config,
                    },
                )

        options_schema = vol.Schema(
            {
                vol.Required(
                    d,
                    default=set(self._hvac_config.get(d, self._system_modes))
                    - self._mandatory_modes,
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=sorted(self._system_modes),
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                        translation_key="available_mode_selector",
                    )
                )
                for d in self.neostat_hcs
            }
        )

        return self.async_show_form(
            step_id=CONF_HVAC_MODES, data_schema=options_schema, errors=errors
        )

    async def async_step_defaults(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the defaults for the custom component."""
        errors: dict[str, str] = {}

        if user_input is not None:
            _LOGGER.debug("user_input: %s", user_input)
            _LOGGER.debug("original config: %s", self._defaults_config)

            self._defaults_config = user_input
            self._defaults_config[CONF_THERMOSTAT_OPTIONS][CONF_STAT_HOLD_DURATION] = (
                int(
                    hold_duration_validation(
                        user_input.get(CONF_THERMOSTAT_OPTIONS, {}).get(
                            CONF_STAT_HOLD_DURATION,
                            {"minutes": DEFAULT_NEOSTAT_HOLD_DURATION},
                        )
                    ).total_seconds()
                    / 60
                )
            )
            self._defaults_config[CONF_TIMER_OPTIONS][CONF_TIMER_HOLD_DURATION] = int(
                hold_duration_validation(
                    user_input.get(CONF_TIMER_OPTIONS, {}).get(
                        CONF_TIMER_HOLD_DURATION,
                        {"minutes": DEFAULT_TIMER_HOLD_DURATION},
                    )
                ).total_seconds()
                / 60
            )

            _LOGGER.debug("updated config: %s", self._defaults_config)

            if not errors:
                # Value of data will be set on the options property of the config_entry instance.
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_HVAC_MODES: self._hvac_config,
                        CONF_DEFAULTS: self._defaults_config,
                    },
                )
        temperature_step = await self.config_entry.runtime_data.coordinator.hub.target_temperature_step()
        options_schema = vol.Schema(
            {
                vol.Required(CONF_THERMOSTAT_OPTIONS): section(
                    vol.Schema(
                        {
                            vol.Required(
                                CONF_STAT_MAX_TEMPERATURE,
                                default=self._defaults_config.get(
                                    CONF_THERMOSTAT_OPTIONS, {}
                                ).get(
                                    CONF_STAT_MAX_TEMPERATURE,
                                    DEFAULT_NEOSTAT_MAX_TEMPERATURE,
                                ),
                            ): NumberSelector(
                                NumberSelectorConfig(
                                    min=1,
                                    max=100,
                                    step=temperature_step,
                                    mode=NumberSelectorMode.BOX,
                                    unit_of_measurement=self._unit_of_measurement,
                                )
                            ),
                            vol.Required(
                                CONF_STAT_MIN_TEMPERATURE,
                                default=self._defaults_config.get(
                                    CONF_THERMOSTAT_OPTIONS, {}
                                ).get(
                                    CONF_STAT_MIN_TEMPERATURE,
                                    DEFAULT_NEOSTAT_MIN_TEMPERATURE,
                                ),
                            ): NumberSelector(
                                NumberSelectorConfig(
                                    min=1,
                                    max=100,
                                    step=temperature_step,
                                    mode=NumberSelectorMode.BOX,
                                    unit_of_measurement=self._unit_of_measurement,
                                )
                            ),
                            vol.Required(
                                CONF_STAT_HOLD_DURATION,
                                default={
                                    "minutes": self._defaults_config.get(
                                        CONF_THERMOSTAT_OPTIONS, {}
                                    ).get(
                                        CONF_STAT_HOLD_DURATION,
                                        DEFAULT_NEOSTAT_HOLD_DURATION,
                                    )
                                },
                            ): DurationSelector(
                                DurationSelectorConfig(
                                    enable_day=False,
                                    enable_millisecond=False,
                                    allow_negative=False,
                                )
                            ),
                            vol.Required(
                                CONF_STAT_HOLD_TEMP,
                                default=self._defaults_config.get(
                                    CONF_THERMOSTAT_OPTIONS, {}
                                ).get(
                                    CONF_STAT_HOLD_TEMP,
                                    DEFAULT_NEOSTAT_TEMPERATURE_BOOST,
                                ),
                            ): NumberSelector(
                                NumberSelectorConfig(
                                    min=1,
                                    max=10,
                                    step=temperature_step,
                                    mode=NumberSelectorMode.BOX,
                                    unit_of_measurement=self._unit_of_measurement,
                                )
                            ),
                        }
                    )
                ),
                vol.Required(CONF_TIMER_OPTIONS): section(
                    vol.Schema(
                        {
                            vol.Required(
                                CONF_TIMER_HOLD_DURATION,
                                default={
                                    "minutes": self._defaults_config.get(
                                        CONF_TIMER_OPTIONS, {}
                                    ).get(
                                        CONF_TIMER_HOLD_DURATION,
                                        DEFAULT_TIMER_HOLD_DURATION,
                                    )
                                },
                            ): DurationSelector(
                                DurationSelectorConfig(
                                    enable_day=False,
                                    enable_millisecond=False,
                                    allow_negative=False,
                                )
                            ),
                        }
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id=CONF_DEFAULTS, data_schema=options_schema, errors=errors
        )

    async def async_step_choose_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle local vs cloud mode selection step."""

        menu_options = {
            CONF_PAIRING: "Pair a new device",
            CONF_PAIRING_REPEATER: "Pair a new repeater",
        }

        return self.async_show_menu(
            step_id="choose_advanced",
            menu_options=menu_options,
        )

    async def async_step_pairing(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Flow to pair new device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            _LOGGER.debug("user_input: %s", user_input)

            async def device_join(hub: NeoHub, timeout: int) -> None:
                return await hub.permit_join(
                    name=user_input[CONF_NAME], timeout_s=timeout
                )

            return await self._async_initiate_pairing(
                device_join, "waiting_for_device_connect", "device_added"
            )

        options_schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
            }
        )

        if self._progress_task and self._progress_task.done():
            return self.async_show_progress_done(next_step_id="device_added")

        return self.async_show_form(
            step_id=CONF_PAIRING, data_schema=options_schema, errors=errors
        )

    async def async_step_pairing_repeater(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Flow to pair new device."""

        async def repeater_join(hub: NeoHub, timeout: int) -> None:
            return await hub.permit_repeater_join(timeout)

        return await self._async_initiate_pairing(
            repeater_join, "waiting_for_repeater_connect", "repeater_added"
        )

    async def _async_initiate_pairing(
        self,
        join_command: Callable[[NeoHub, int], Awaitable[Any]],
        progress_action: str,
        next_step_id: str,
        timeout: int = 120,
    ) -> ConfigFlowResult:
        if not self._progress_task:
            self._progress_task = self.hass.async_create_task(
                self._async_await_device_join(float(timeout))
            )
            hub: NeoHub = self.config_entry.runtime_data.coordinator.hub
            await join_command(hub, timeout)
        if not self._progress_task.done():
            # Show initial progress UI
            return self.async_show_progress(
                progress_action=progress_action,
                progress_task=self._progress_task,
                description_placeholders={"timeout": str(timeout)},
            )

        return self.async_show_progress_done(next_step_id=next_step_id)

    async def _async_await_device_join(
        self, timeout: float = 120.0, poll_interval: float = 10.0
    ) -> str | None:
        """Background task to handle the timer and progress updates."""
        # try:
        start_time = asyncio.get_running_loop().time()
        last_poll_time = start_time
        while True:
            current_time = asyncio.get_running_loop().time()
            elapsed = current_time - start_time

            # Calculate and update progress percentage (fills the bar over time)
            progress = elapsed / timeout
            self.async_update_progress(1 - progress)

            if elapsed >= timeout or current_time - last_poll_time >= poll_interval:
                await self.config_entry.runtime_data.coordinator.async_request_refresh()
                last_poll_time = current_time

            self._new_devices, _ = self.config_entry.runtime_data.coordinator.data

            if len(self._new_devices) > len(self._devices):
                return

            if elapsed >= timeout:
                return
            # Sleep briefly to update progress smoothly
            await asyncio.sleep(timeout / 100)

    async def async_step_repeater_added(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Check repeater added."""
        if not self._new_devices or len(self._new_devices) == len(self._devices):
            return self.async_abort(reason="repeater_add_failed")
        self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
        new_keys = self._new_devices.keys() - self._devices.keys()
        return self.async_abort(
            reason="repeater_added",
            description_placeholders={"repeater_name": ",".join(new_keys)},
        )

    async def async_step_device_added(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Check device added."""
        if not self._new_devices or len(self._new_devices) == len(self._devices):
            return self.async_abort(reason="device_add_failed")
        self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
        new_keys = self._new_devices.keys() - self._devices.keys()
        return self.async_abort(
            reason="device_added",
            description_placeholders={"device_name": ",".join(new_keys)},
        )
