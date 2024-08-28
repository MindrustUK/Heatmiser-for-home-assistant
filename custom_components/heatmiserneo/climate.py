# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""
homeassistant.components.climate.heatmiserneo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Heatmiser NeoStat control via Heatmiser Neo-hub
"""

import logging
import asyncio
from collections import OrderedDict

import voluptuous as vol

from homeassistant.components.climate import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    FAN_AUTO,
    FAN_ON,
    PRESET_AWAY,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
    UnitOfTemperature
)

from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from neohubapi.neohub import NeoHub, NeoStat, HCMode
from .const import DOMAIN, HUB, COORDINATOR, CONF_HVAC_MODES, AvailableMode

from .const import (
    ATTR_HOLD_DURATION,
    ATTR_HOLD_TEMPERATURE,
    SERVICE_HOLD_OFF,
    SERVICE_HOLD_ON,
)

_LOGGER = logging.getLogger(__name__)


SUPPORT_FLAGS = 0
THERMOSTATS = "thermostats"


hvac_mode_mapping = {
    AvailableMode.AUTO: HVACMode.HEAT_COOL,
    AvailableMode.COOL: HVACMode.COOL,
    AvailableMode.VENT: HVACMode.FAN_ONLY,
    AvailableMode.HEAT: HVACMode.HEAT,
}


async def async_setup_entry(hass, entry, async_add_entities):
    hub: NeoHub = hass.data[DOMAIN][HUB]
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][COORDINATOR]

    (devices_data, system_data) = coordinator.data
    thermostats = {device.name: device for device in devices_data['neo_devices']}

    hvac_config = (
        entry.options[CONF_HVAC_MODES] if CONF_HVAC_MODES in entry.options else {}
    )
    _LOGGER.debug(f"hvac_config: {hvac_config}")
    for config in hvac_config:
        _LOGGER.debug(
            f"Overriding the default HVAC modes from {thermostats[config].available_modes} to {hvac_config[config]} for the {config} climate entity."
        )
        thermostats[config].available_modes = hvac_config[config]

    temperature_unit = system_data.CORF
    temperature_step = await hub.target_temperature_step

    entities = []
    for device in thermostats.values():
        if device.device_type in [1, 2, 7, 12, 13]:
            if not device.time_clock_mode:
                entities.append(NeoStatEntity(device, coordinator, hub, temperature_unit, temperature_step))

    _LOGGER.info(f"Adding Thermostats: {entities}")
    async_add_entities(entities, True)

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_HOLD_ON,
        {
            vol.Required(ATTR_HOLD_DURATION, default=1): object,
            vol.Required(ATTR_HOLD_TEMPERATURE, default=20): int,
        },
        "set_hold",
    )

    platform.async_register_entity_service(
        SERVICE_HOLD_OFF,
        {},
        "unset_hold",
    )


class NeoStatEntity(CoordinatorEntity, ClimateEntity):
    """Represents a Heatmiser neoStat thermostat."""

    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
            self,
            neostat: NeoStat,
            coordinator: DataUpdateCoordinator,
            hub: NeoHub,
            unit_of_measurement,
            temperature_step
    ):

        super().__init__(coordinator)
        _LOGGER.debug(f"Creating {neostat}")

        self._neostat = neostat
        self._coordinator = coordinator
        self._hub = hub
        self._unit_of_measurement = unit_of_measurement
        self._target_temperature_step = temperature_step
        self._hvac_modes = []
        if hasattr(neostat, "standby"):
            self._hvac_modes.append(HVACMode.OFF)
        for mode in neostat.available_modes:
            self._hvac_modes.append(hvac_mode_mapping[mode])

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        neo_devices = {device.name: device for device in devices['neo_devices']}
        return neo_devices[self.name]

    async def async_set_hvac_mode(self, hvac_mode):
        """Set hvac mode."""
        _LOGGER.info(f"{self.name} : Executing set_hvac_mode() with: {hvac_mode}")
        _LOGGER.debug(f"self.data: {self.data}")

        hc_mode: HCMode = None
        if hvac_mode == HVACMode.HEAT:
            hc_mode = HCMode.HEATING
        elif hvac_mode == HVACMode.COOL:
            hc_mode = HVACMode.COOLING
        elif hvac_mode == HVACMode.HEAT_COOL:
            hc_mode = HCMode.AUTO
        elif hvac_mode == HVACMode.FAN_ONLY:
            hc_mode = HCMode.VENT

        # Optimistically update the mode so that the UI feels snappy.
        # The value will be confirmed next time we get new data.
        self.data.hc_mode = hc_mode
        self.async_schedule_update_ha_state(False)

        if hc_mode:
            set_hc_mode_task = asyncio.create_task(self._neostat.set_hc_mode(hc_mode))
            response = await set_hc_mode_task
            _LOGGER.info(
                f"{self.name} : Called set_hc_mode() with: {hc_mode} (response: {response})"
            )

        frost: bool = True if hvac_mode == HVAC_MODE_OFF else False
        set_frost_task = asyncio.create_task(self._neostat.set_frost(frost))
        response = await set_frost_task
        _LOGGER.info(
            f"{self.name} : Called set_frost() with: {frost} (response: {response})"
        )

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        _LOGGER.info(f"{self.name} : Executing set_temperature() with: {kwargs}")
        _LOGGER.debug(f"self.data: {self.data}")

        low_temp = kwargs.get(ATTR_TEMPERATURE) or kwargs.get(ATTR_TARGET_TEMP_LOW)
        high_temp = kwargs.get(ATTR_TARGET_TEMP_HIGH)

        set_target_temperature_task = asyncio.create_task(
            self._neostat.set_target_temperature(low_temp)
        )
        response = await set_target_temperature_task
        if response:
            _LOGGER.info(
                f"{self.name} : Called set_target_temperature with: {low_temp} (response: {response})"
            )

        set_target_cool_temperature_task = asyncio.create_task(
            self._neostat.set_cool_temp(high_temp)
        )
        response = await set_target_cool_temperature_task
        if response:
            _LOGGER.info(
                f"{self.name} : Called set_cool_temp with: {high_temp} (response: {response})"
            )

        # The change of target temperature may trigger a change in the current hvac_action
        # so we schedule a refresh to get new data asap.
        await self._coordinator.async_request_refresh()

    @property
    def available(self):
        """Return true if the entity is available."""
        if self.data.offline:
            return False
        return True

    @property
    def current_temperature(self):
        """Returns the current temperature."""
        if self.data.offline:
            return None

        # Check if the current temperature is 127 or 255, Hub probably lost connection?
        # Also handle possible floats.
        if self.data.temperature in ["127", "127.0", "255", "255.0"]:
            _LOGGER.error(
                f"Error: Climate entity '{self._neostat.name}' has an invalid current_temperature value: "
                f"{self.data.temperature}, Hub lost connection?"
            )
            return None
        
        return float(self.data.temperature)

    @property
    def device_info(self):
        return {
            "identifiers": {("Heatmiser Neo Device", self._neostat.device_id)},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": f"Device Type: {self._neostat.device_type}",
            "suggested_area": self._neostat.name,
            "sw_version": self.data.stat_version
        }

    @property
    def extra_state_attributes(self):
        """Return the additional state attributes."""
        attributes = OrderedDict()

        attributes['device_type'] = self.data.device_type
        attributes['low_battery'] = self.data.low_battery
        attributes['offline'] = self.data.offline
        attributes['standby'] = self.data.standby
        attributes['hold_on'] = self.data.hold_on
        attributes['hold_time'] = ':'.join(str(self.data.hold_time).split(':')[:2])
        attributes['hold_temp'] = self.data.hold_temp
        attributes['floor_temperature'] = self.data.current_floor_temperature
        attributes['preheat_active'] = self.data.preheat_active
        attributes['hc_mode'] = self.data.hc_mode
        attributes['sensor_mode'] = self.data.sensor_mode

        return attributes

    @property
    def name(self):
        """Returns the name."""
        return self._neostat.name

    @property
    def hvac_action(self):
        # See: https://developers.home-assistant.io/docs/core/entity/climate/
        """The current HVAC action (heating, cooling)"""
        if self.data.standby:
            return HVACAction.OFF
        elif self.data.preheat_active:
            return HVACAction.PREHEATING
        elif self.data.cool_on:
            return HVACAction.COOLING
        elif self.data.heat_on:
            return HVACAction.HEATING
        elif self.data.fan_speed != "Off":
            return HVACAction.FAN  # Should fan be combined? Ie can you have fan on and other functions together?
        else:
            return HVACAction.IDLE

    @property
    def hvac_mode(self):
        """Return The current operation (e.g. heat, cool, idle). Used to determine state."""
        if self.data.standby:
            return HVACMode.OFF
        elif self.data.hc_mode == "COOLING":
            return HVACMode.COOL
        elif self.data.hc_mode == "HEATING":
            return HVACMode.HEAT
        elif self.data.hc_mode == "AUTO":
            return HVACMode.HEAT_COOL
        elif self.data.hc_mode == "VENT":
            return HVACMode.FAN_ONLY

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return self._hvac_modes

    async def set_hold(self, hold_duration: object, hold_temperature: int):
        """
        Sets Hold for Zone
        """
        _LOGGER.warning(
            f"{self.name} : Executing set_hold() with duration: {hold_duration}, temperature: {hold_temperature}")
        _LOGGER.debug(f"self.data: {self.data}")

        hold_hours = 0
        hold_minutes = 0
        if str(hold_duration).count(":") > 0:
            try:
                # Try to extract hours and minutes from dict
                hold_hours = int(hold_duration['hours'])
                hold_minutes = int(hold_duration['minutes'])
                _LOGGER.debug(f"{self.name} : Duration interpreted from object")
            except:
                # Try to extract hours from string
                hold_hours, hold_minutes, _ = hold_duration.split(':')
                hold_hours = int(hold_hours)
                hold_minutes = int(hold_minutes)
                _LOGGER.debug(f"{self.name} : Duration interpreted from string")
        else:
            hold_hours = int(hold_duration)
            _LOGGER.debug(f"{self.name} : Duration interpreted from number")

        if hold_minutes > 59:
            _hold_revised_minutes = hold_minutes % 60
            hold_hours += int((hold_minutes - _hold_revised_minutes) / 60)
            hold_minutes = _hold_revised_minutes
        if hold_hours > 99:
            hold_hours = 99

        message = {"HOLD": [{"temp": hold_temperature, "hours": hold_hours, "minutes": hold_minutes, "id": self.name},
                            [self.name]]}
        reply = {"result": "temperature on hold"}

        result = await self._hub._send(message, reply)

        # Optimistically update the mode so that the UI feels snappy.
        # The value will be confirmed next time we get new data.

        self.data.hold_on = True
        self.data.hold_time = str(f"{str(hold_hours)}:{str(hold_minutes).ljust(2, '0')}")
        self.data.hold_temp = int(hold_temperature)
        self.async_schedule_update_ha_state(False)

        return result

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def supported_features(self):
        """Return the list of supported features."""
        hvac_mode = self.hvac_mode
        if hvac_mode == HVACMode.HEAT:
            return SUPPORT_FLAGS | ClimateEntityFeature.TARGET_TEMPERATURE
        elif hvac_mode == HVACMode.COOL:
            return SUPPORT_FLAGS | ClimateEntityFeature.TARGET_TEMPERATURE
        elif hvac_mode == HVACMode.OFF:
            return SUPPORT_FLAGS
        elif hvac_mode == HVACMode.HEAT_COOL:
            return SUPPORT_FLAGS | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        elif hvac_mode == HVACMode.FAN_ONLY:
            return SUPPORT_FLAGS | ClimateEntityFeature.TARGET_TEMPERATURE
        else:
            _LOGGER.error(f"Unsupported hvac mode: {hvac_mode}")
            return SUPPORT_FLAGS

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return float(self.data.target_temperature)

    @property
    def target_temperature_high(self):
        """Return the temperature we try to reach."""
        return float(self.data.cool_temp)

    @property
    def target_temperature_low(self):
        """Return the temperature we try to reach."""
        return float(self.data.target_temperature)

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        # TODO: Step for V1 and V2 varies?
        return self._target_temperature_step

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        if self._unit_of_measurement == "C":
            return UnitOfTemperature.CELSIUS
        if self._unit_of_measurement == "F":
            return UnitOfTemperature.FAHRENHEIT
        return self._unit_of_measurement

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._neostat.device_id}_neostat"

    async def unset_hold(self):
        """
        Unsets Hold for Zone
        """

        message = {"HOLD": [{"temp": 20, "hours": 0, "minutes": 0, "id": self.name}, [self.name]]}
        reply = {"result": "temperature on hold"}

        result = await self._hub._send(message, reply)

        # Optimistically update the mode so that the UI feels snappy.
        # The value will be confirmed next time we get new data.
        self.data.hold_on = False
        self.data.hold_time = str("0:00")
        self.data.hold_temp = 20
        self.async_schedule_update_ha_state(False)

        return result
