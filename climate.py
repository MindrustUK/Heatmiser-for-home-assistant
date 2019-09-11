"""
homeassistant.components.climate.heatmiserneo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Heatmiser NeoStat control via Heatmiser Neo-hub
Code largely ripped off and glued togehter from:
demo.py, nest.py and light/hyperion.py for the json elements
"""

from homeassistant.components.climate import ClimateDevice, PLATFORM_SCHEMA
import logging
import voluptuous as vol
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
from homeassistant.const import (CONF_HOST,CONF_PORT,CONF_NAME)
import homeassistant.helpers.config_validation as cv
import socket
import json

_LOGGER = logging.getLogger(__name__)

VERSION = '2.0.2'

SUPPORT_FLAGS = 0

# Heatmiser does support all lots more stuff, but only heat for now.
#hvac_modes=[HVAC_MODE_HEAT_COOL, HVAC_MODE_COOL, HVAC_MODE_HEAT, HVAC_MODE_OFF]
# Heatmiser doesn't really have an off mode - standby is a preset - implement later
hvac_modes = [HVAC_MODE_HEAT]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.port,
    }
)

# Fix this when I figure out why my config won't read in. Voluptuous schma thing.
# Excludes time clocks from being included if set to True
ExcludeTimeClock = False

def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Sets up a Heatmiser Neo-Hub And Returns Neostats"""
    host = config.get(CONF_HOST, None)
    port = config.get(CONF_PORT, 4242)

    thermostats = []

    NeoHubJson = HeatmiserNeostat(TEMP_CELSIUS, False, host, port).json_request({"INFO": 0})

    _LOGGER.debug(NeoHubJson)

    for device in NeoHubJson['devices']:
        if device['DEVICE_TYPE'] != 6:
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

            if (('TIMECLOCK' in device['STAT_MODE']) and (ExcludeTimeClock == True)):
              _LOGGER.debug("Found a Neostat configured in timer mode named: %s skipping" % device['device'])
            else:
              thermostats.append(HeatmiserNeostat(temperature_unit, away, host, port, name))

        elif device['DEVICE_TYPE'] == 6:
            _LOGGER.debug("Found a Neoplug named: %s skipping" % device['device'])

    _LOGGER.info("Adding Thermostats: %s " % thermostats)
    add_devices(thermostats)


class HeatmiserNeostat(ClimateDevice):
    """ Represents a Heatmiser Neostat thermostat. """
    def __init__(self, unit_of_measurement, away, host, port, name="Null"):
        self._name = name
        self._unit_of_measurement = unit_of_measurement
        self._away = away
        self._host = host
        self._port = port
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
        response = self.json_request({"SET_TEMP": [int(kwargs.get(ATTR_TEMPERATURE)), self._name]})
        if response:
            _LOGGER.info("set_temperature response: %s " % response)
            # Need check for success here
            # {'result': 'temperature was set'}

    def update(self):
        """ Get Updated Info. """
        _LOGGER.debug("Entered update(self)")
        response = self.json_request({"INFO": 0})
        if response:
            # Add handling for mulitple thermostats here
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

                # Figure out the current mode based on whether cooling is enabled - should verify that this is correct
                if device["COOLING_ENABLED"] == True:
                    self._hvac_mode = HVAC_MODE_HEAT
                else:
                    self._hvac_mode = HVAC_MODE_COOL

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

    def json_request(self, request=None, wait_for_response=False):
        """ Communicate with the json server. """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)

        try:
            sock.connect((self._host, self._port))
        except OSError:
            sock.close()
            return False

        if not request:
            # no communication needed, simple presence detection returns True
            sock.close()
            return True

        _LOGGER.debug("json_request: %s " % request)

        sock.send(bytearray(json.dumps(request) + "\0\r", "utf-8"))
        try:
            buf = sock.recv(4096)
        except socket.timeout:
            # something is wrong, assume it's offline
            sock.close()
            return False

        # read until a newline or timeout
        buffering = True
        while buffering:
            if "\n" in str(buf, "utf-8"):
                response = str(buf, "utf-8").split("\n")[0]
                buffering = False
            else:
                try:
                    more = sock.recv(4096)
                except socket.timeout:
                    more = None
                if not more:
                    buffering = False
                    response = str(buf, "utf-8")
                else:
                    buf += more

        sock.close()

        response = response.rstrip('\0')

        _LOGGER.debug("json_response: %s " % response)

        return json.loads(response, strict=False)
