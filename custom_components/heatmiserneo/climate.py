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

from .heatmiserneo import NeoHub
from .const import (DOMAIN,HUB)

_LOGGER = logging.getLogger(__name__)


SUPPORT_FLAGS = 0

# Heatmiser does support all lots more stuff, but only heat for now.
#hvac_modes=[HVAC_MODE_HEAT_COOL, HVAC_MODE_COOL, HVAC_MODE_HEAT, HVAC_MODE_OFF]
# Heatmiser doesn't really have an off mode - standby is a preset - implement later
hvac_modes = [HVAC_MODE_OFF, HVAC_MODE_HEAT]



async def async_setup_entry(hass, entry, async_add_entities):

    hub = hass.data[DOMAIN][HUB]

    thermostats = []

    NeoHubJson = hub.json_request({"INFO": 0})

    _LOGGER.debug(NeoHubJson)

    for device in NeoHubJson['devices']:
        if (device['DEVICE_TYPE'] != 6) and ('THERMOSTAT' in device['STAT_MODE']):
            name = device['device']
            tmptempfmt = device['TEMPERATURE_FORMAT']
            if (tmptempfmt == False) or (tmptempfmt.upper() == "C"):
                temperature_unit = TEMP_CELSIUS
            else:
                temperature_unit = TEMP_FAHRENHEIT
            away = device['AWAY']
            current_temperature = device['CURRENT_TEMPERATURE']
            set_temperature = device['CURRENT_SET_TEMPERATURE']

            _LOGGER.info("Thermostat Name: %s " % name)
            _LOGGER.info("Thermostat Away Mode: %s " % away)
            _LOGGER.info("Thermostat Current Temp: %s " % current_temperature)
            _LOGGER.info("Thermostat Set Temp: %s " % set_temperature)
            _LOGGER.info("Thermostat Unit Of Measurement: %s " % temperature_unit)

            thermostats.append(HeatmiserNeostat(temperature_unit, away, hub, name))

    _LOGGER.info("Adding Thermostats: %s " % thermostats)
    async_add_entities(thermostats)


class HeatmiserNeostat(ClimateEntity):
    """ Represents a Heatmiser Neostat thermostat. """
    def __init__(self, unit_of_measurement, away, hub, name="Null"):
        self._hub = hub
        self._name = name
        self._unit_of_measurement = unit_of_measurement
        self._away = away
        #self._type = type Neostat vs Neostat-e
        self._hvac_action = None
        self._hvac_mode = None
        self._hvac_modes = hvac_modes
        self._support_flags = SUPPORT_FLAGS
        self._support_flags = self._support_flags | SUPPORT_TARGET_TEMPERATURE
        self.update()

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
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._name

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
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
    def current_humidity(self):
        """Return the current humidity."""
        return self._current_humidity

    @property
    def target_humidity(self):
        """Return the humidity we try to reach."""
        return self._target_humidity

    #@property
    #def target_temperature(self):
    #    """ Returns the temperature we try to reach. """
    #    return self._target_temperature

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

    # @property
    # def preset_mode(self):
    #     """Return preset mode."""
    #     return self._preset

    # @property
    # def preset_modes(self):
    #     """Return preset modes."""
    #     return self._preset_modes

    def set_temperature(self, **kwargs):
        """ Set new target temperature. """
        response = self._hub.json_request({"SET_TEMP": [int(kwargs.get(ATTR_TEMPERATURE)), self._name]})
        if response:
            _LOGGER.info("set_temperature response: %s " % response)
            # Need check for success here
            # {'result': 'temperature was set'}

    def set_hvac_mode(self, hvac_mode):
        """Set hvac mode."""
        if hvac_mode == HVAC_MODE_HEAT:
            self._hvac_mode = HVAC_MODE_HEAT
            mode = "FROST_OFF"
        elif hvac_mode == HVAC_MODE_OFF:
            self._hvac_mode = HVAC_MODE_OFF
            mode = "FROST_ON"
        else:
            _LOGGER.error("Unrecognized hvac mode: %s", hvac_mode)
            return

        response = self._hub.json_request({mode: [self._name]})
        if response:
            _LOGGER.info("set_hvac_mode response: %s " % response)

    def update(self):
        """ Get Updated Info. """
        _LOGGER.debug("Entered update(self)")
        response = self._hub.json_request({"INFO": 0})
        if response:
            # Add handling for multiple thermostats here
            _LOGGER.debug("update() json response: %s " % response)
            # self._name = device['device']
            for device in response['devices']:
              if self._name == device['device']:
                tmptempfmt = device["TEMPERATURE_FORMAT"]
                if (tmptempfmt == False) or (tmptempfmt.upper() == "C"):
                  self._temperature_unit = TEMP_CELSIUS
                else:
                  self._temperature_unit = TEMP_FAHRENHEIT
                self._away = device['AWAY']
                self._target_temperature =  round(float(device["CURRENT_SET_TEMPERATURE"]), 2)
                self._current_temperature = round(float(device["CURRENT_TEMPERATURE"]), 2)
                self._current_humidity = round(float(device["HUMIDITY"]), 2)

                if device['STANDBY']:
                    self._hvac_mode = HVAC_MODE_OFF
                elif device["COOLING_ENABLED"] == True:
                    self._hvac_mode = HVAC_MODE_COOL
                else:
                    self._hvac_mode = HVAC_MODE_HEAT

                # Figure out current action based on Heating / Cooling flags
                if device["HEATING"] == True:
                    self._hvac_action = CURRENT_HVAC_HEAT
                    _LOGGER.debug("Heating")
                elif device["COOLING"] == True:
                    self._hvac_action = CURRENT_HVAC_COOL
                    _LOGGER.debug("Cooling")
                else:
                    self._hvac_action = CURRENT_HVAC_IDLE
                    _LOGGER.debug("Idle")
        return False

