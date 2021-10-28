
# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""
homeassistant.components.climate.heatmiserneo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Heatmiser NeoStat control via Heatmiser Neo-hub
Code largely ripped off and glued together from:
demo.py, nest.py and light/hyperion.py for the json elements
"""

import logging
import asyncio

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    HVAC_MODE_COOL,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT

from .const import DOMAIN, HUB
from neohubapi.neohub import NeoHub, NeoStat, HCMode

_LOGGER = logging.getLogger(__name__)


SUPPORT_FLAGS = 0

# Heatmiser doesn't really have an off mode - standby is a preset - implement later
hvac_modes = [HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_HEAT_COOL, HVAC_MODE_FAN_ONLY]


async def async_setup_entry(hass, entry, async_add_entities):

    hub: NeoHub = hass.data[DOMAIN][HUB]
    _, devices = await hub.get_live_data()

    system_data = await hub.get_system()
    temperature_unit = system_data.CORF
    thermostats = [HeatmiserNeostat(hub, stat, temperature_unit) for stat in devices['thermostats']]
    _LOGGER.info("Adding Thermostats: %s " % thermostats)
    async_add_entities(thermostats, True)


class HeatmiserNeostat(ClimateEntity):
    """ Represents a Heatmiser Neostat thermostat. """
    def __init__(self, hub: NeoHub, neostat: NeoStat, unit_of_measurement):
        self._neostat = neostat
        self._hub = hub
        self._unit_of_measurement = unit_of_measurement
        self._away = None
        # self._type = type Neostat vs Neostat-e
        self._hvac_action = None
        self._hvac_mode = None
        self._hvac_modes = hvac_modes
        self._target_temperature_high = None
        self._target_temperature_low = None
        self._support_flags = SUPPORT_FLAGS

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    @property
    def should_poll(self):
        """ No polling needed for a demo thermostat. """
        return True

    @property
    def name(self):
        """ Returns the name. """
        return self._neostat.name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._neostat.name

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        if self._unit_of_measurement == "C":
            return TEMP_CELSIUS
        if self._unit_of_measurement == "F":
            return TEMP_FAHRENHEIT
        return self._unit_of_measurement

    @property
    def current_temperature(self):
        """ Returns the current temperature. """
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def target_temperature_high(self):
        """Return the temperature we try to reach."""
        return self._target_temperature_high

    @property
    def target_temperature_low(self):
        """Return the temperature we try to reach."""
        return self._target_temperature_low

#    @property
#    def current_humidity(self):
#        """Return the current humidity."""
#        return self._current_humidity

#    @property
#    def target_humidity(self):
#        """Return the humidity we try to reach."""
#        return self._target_humidity

    @property
    def hvac_action(self):
        """Return current activity ie. currently heating, cooling, idle."""
        return self._hvac_action

    @property
    def hvac_mode(self):
        """Return current operation mode ie. heat, cool, off."""
        return self._hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return self._hvac_modes
    
    @property
    def device_info(self):
        return {
            "identifiers": {("HeatMiser NeoStat", self._neostat.name)},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": "NeoStat",
            "suggested_area": self._neostat.name,
        }

    async def async_set_temperature(self, **kwargs):
        """ Set new target temperature. """
        _LOGGER.debug("set_temperature ")
        low_temp = kwargs.get(ATTR_TEMPERATURE) or kwargs.get(ATTR_TARGET_TEMP_LOW)
        high_temp = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        response = await self._neostat.set_target_temperature(low_temp)
        if response:
            _LOGGER.info("set_temperature TEMPERATURE to %s response: %s " % (low_temp, response))
        response = await self._neostat.set_cool_temp(high_temp)
        if response:
            _LOGGER.info("set_temperature TEMP HIGH to %s response: %s " % (high_temp, response))

        await self.async_update()

    def update_hvac_mode(self, hvac_mode):
        """
          Updates the home assistant entity according to the given hvac mode
        """
        _LOGGER.debug("update hvac_mode %s" % hvac_mode)
        if hvac_mode == HVAC_MODE_HEAT:
            self._hvac_mode = HVAC_MODE_HEAT
            self._support_flags = SUPPORT_FLAGS | SUPPORT_TARGET_TEMPERATURE
        elif hvac_mode == HVAC_MODE_COOL:
            self._hvac_mode = HVAC_MODE_COOL
            self._support_flags = SUPPORT_FLAGS | SUPPORT_TARGET_TEMPERATURE
        elif hvac_mode == HVAC_MODE_OFF:
            self._hvac_mode = HVAC_MODE_OFF
        elif hvac_mode == HVAC_MODE_HEAT_COOL:
            self._hvac_mode = HVAC_MODE_HEAT_COOL
            self._support_flags = SUPPORT_FLAGS | SUPPORT_TARGET_TEMPERATURE_RANGE
        elif hvac_mode == HVAC_MODE_FAN_ONLY:
            self._hvac_mode = HVAC_MODE_FAN_ONLY
            self._support_flags = SUPPORT_FLAGS | SUPPORT_TARGET_TEMPERATURE
        else:
            _LOGGER.error("Unsupported hvac mode: %s", hvac_mode)
            return

    async def async_set_hvac_mode(self, hvac_mode):
        """Set hvac mode."""
        frost: bool = False
        hc_mode: HCMode = None

        self.update_hvac_mode(hvac_mode)
        if hvac_mode == HVAC_MODE_HEAT:
            hc_mode = HCMode.HEATING
        elif hvac_mode == HVAC_MODE_COOL:
            hc_mode = HCMode.COOLING
        elif hvac_mode == HVAC_MODE_OFF:
            frost = True
        elif hvac_mode == HVAC_MODE_HEAT_COOL:
            hc_mode = HCMode.AUTO
        elif hvac_mode == HVAC_MODE_FAN_ONLY:
            hc_mode = HCMode.VENT
        else:
            _LOGGER.error("Unsupported hvac mode: %s", hvac_mode)
            return

        set_hc_mode_task = None
        if hc_mode:
            set_hc_mode_task = asyncio.create_task(self._neostat.set_hc_mode(hc_mode))
        set_frost_task = asyncio.create_task(self._neostat.set_frost(frost))

        if set_hc_mode_task:
            response = await set_hc_mode_task
            _LOGGER.info("set_hc_mode %s response: %s " % (hc_mode, response))

        response = await set_frost_task
        _LOGGER.info("set_frost %s response: %s " % (frost, response))

    async def async_update(self):
        """ Get Updated Info. """
        _LOGGER.debug("Entered update(self)")
        _, devices = await self._hub.get_live_data()
        for thermostat in devices['thermostats']:
            if self._neostat.name == thermostat.name:
                self._away = thermostat.away
                self._target_temperature = round(float(thermostat.target_temperature), 2)
                self._current_temperature = round(float(thermostat.temperature), 2)

                if thermostat.standby:
                    self.update_hvac_mode(HVAC_MODE_OFF)
                else:
                    # We are in heating mode by default as some devices only support this mode.
                    hc_mode = HCMode(thermostat.hc_mode)
                    if hc_mode == HCMode.AUTO:
                        self.update_hvac_mode(HVAC_MODE_HEAT_COOL)
                    elif hc_mode == HCMode.VENT:
                        self.update_hvac_mode(HVAC_MODE_FAN_ONLY)
                    elif hc_mode == HCMode.COOLING:
                        self.update_hvac_mode(HVAC_MODE_COOL)
                    else:
                        self.update_hvac_mode(HVAC_MODE_HEAT)

                if (self._hvac_mode in (HVAC_MODE_COOL, HVAC_MODE_HEAT_COOL)):
                    self._target_temperature_high = round(float(thermostat.cool_temp), 2)
                    self._target_temperature_low = round(float(thermostat.target_temperature), 2)

                if thermostat.heat_on:
                    self._hvac_action = CURRENT_HVAC_HEAT
                    _LOGGER.debug("Heating")
                elif thermostat.cool_on:
                    self._hvac_action = CURRENT_HVAC_COOL
                    _LOGGER.debug("Cooling")
                else:
                    self._hvac_action = CURRENT_HVAC_IDLE
                    _LOGGER.debug("Idle")

                # TODO implement support for CURRENT_HVAC_OFF
