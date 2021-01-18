
# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""
homeassistant.components.climate.heatmiserneo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Heatmiser NeoStat control via Heatmiser Neo-hub
Code largely ripped off and glued together from:
demo.py, nest.py and light/hyperion.py for the json elements
"""

import logging

from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    HVAC_MODES,
    SUPPORT_AUX_HEAT,
    SUPPORT_FAN_MODE,
    SUPPORT_PRESET_MODE,
    SUPPORT_SWING_MODE,
    SUPPORT_TARGET_HUMIDITY,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
    HVAC_MODE_AUTO,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT

from .const import DOMAIN, HUB
from neohubapi.neohub import NeoHub, NeoStat

_LOGGER = logging.getLogger(__name__)


SUPPORT_FLAGS = 0

# Heatmiser does support all lots more stuff, but only heat for now.
#hvac_modes=[HVAC_MODE_HEAT_COOL, HVAC_MODE_COOL, HVAC_MODE_HEAT, HVAC_MODE_OFF]
# Heatmiser doesn't really have an off mode - standby is a preset - implement later
hvac_modes = [HVAC_MODE_OFF, HVAC_MODE_HEAT]


async def async_setup_entry(hass, entry, async_add_entities):

    hub: Neohub = hass.data[DOMAIN][HUB]
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
        #self._type = type Neostat vs Neostat-e
        self._hvac_action = None
        self._hvac_mode = None
        self._hvac_modes = hvac_modes
        self._support_flags = SUPPORT_FLAGS
        self._support_flags = self._support_flags | SUPPORT_TARGET_TEMPERATURE

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

    async def async_set_temperature(self, **kwargs):
        """ Set new target temperature. """
        response = await self._neostat.set_target_temperature(kwargs.get(ATTR_TEMPERATURE))
        if response:
            _LOGGER.info("set_temperature response: %s " % response)

    async def async_set_hvac_mode(self, hvac_mode):
        """Set hvac mode."""
        frost: bool
        if hvac_mode == HVAC_MODE_HEAT:
            self._hvac_mode = HVAC_MODE_HEAT
            frost = False
        elif hvac_mode == HVAC_MODE_OFF:
            self._hvac_mode = HVAC_MODE_OFF
            frost = True
        else:
            _LOGGER.error("Unrecognized hvac mode: %s", hvac_mode)
            return

        response = await self._neostat.set_frost(frost)
        if response:
            _LOGGER.info("set_hvac_mode response: %s " % response)

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
                    self._hvac_mode = HVAC_MODE_OFF
                else:
                    self._hvac_mode = HVAC_MODE_HEAT

                if thermostat.heat_on:
                    self._hvac_action = CURRENT_HVAC_HEAT
                    _LOGGER.debug("Heating")
                else:
                    self._hvac_action = CURRENT_HVAC_IDLE
                    _LOGGER.debug("Idle")

