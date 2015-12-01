"""
homeassistant.components.thermostat.heatmiserneo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Heatmiser NeoStat control via Heatmiser Neo-hub
Code largely ripped off and glued togehter from:
demo.py, nest.py and light/hyperion.py for the json elements
"""

from homeassistant.components.thermostat import ThermostatDevice
from homeassistant.const import TEMP_CELCIUS, TEMP_FAHRENHEIT, CONF_HOST #, CONF_PORT

import logging
import socket
import json

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """ Sets up a Heatmiser Neo-Hub And Returns Neostats"""
    host = config.get(CONF_HOST, None)
    port = config.get("port", 4242)

    thermostats = []

    NeoHubJson = HeatmiserNeostat(TEMP_CELCIUS, False, host, port).json_request({"INFO": "0"})

    #_LOGGER.info(NeoHubJson)

    for device in NeoHubJson['devices']:
        name = device['device']
        unit_of_measurement = TEMP_CELCIUS
        away = device['AWAY']
        current_temperature = device['CURRENT_TEMPERATURE']
        set_temperature = device['CURRENT_SET_TEMPERATURE']

        _LOGGER.info("Thermostat Name: %s " % name)
        _LOGGER.info("Thermostat Away Mode: %s " % away)
        _LOGGER.info("Thermostat Current Temp: %s " % current_temperature)
        _LOGGER.info("Thermostat Set Temp: %s " % set_temperature)
        _LOGGER.info("Thermostat Unit Of Measurement: %s " % unit_of_measurement)

        thermostats.append(HeatmiserNeostat(unit_of_measurement, away, host, port, name))

    _LOGGER.info("Adding Thermostats: %s " % thermostats)
    add_devices_callback(thermostats)


class HeatmiserNeostat(ThermostatDevice):
    """ Represents a Heatmiser Neostat thermostat. """
    def __init__(self, unit_of_measurement, away, host, port, name="Null"):
        self._name = name
        self._unit_of_measurement = unit_of_measurement
        self._away = away
        self._host = host
        self._port = port
        #self._type = type Neostat vs Neostat-e
        self._operation = "Null"

    @property
    def should_poll(self):
        """ No polling needed for a demo thermostat. """
        return True

    @property
    def name(self):
        """ Returns the name. """
        return self._name

    @property
    def operation(self):
        """ Returns current operation. heat, cool idle """
        return self._operation

    @property
    def unit_of_measurement(self):
        """ Returns the unit of measurement. """
        return self._unit_of_measurement

    @property
    def current_temperature(self):
        """ Returns the current temperature. """
        #print("Self %s" % self)
        #print(dir(self))
        response = self.json_request({"INFO": "0"})
        if response:
            _LOGGER.info("response: %s " % response)
            self._current_temperature = float(response['devices'][0]["CURRENT_TEMPERATURE"])
            return round(self._current_temperature, 2)
        return False

    @property
    def target_temperature(self):
        """ Returns the temperature we try to reach. """
        response = self.json_request({"INFO": "0"})
        if response:
            _LOGGER.debug("response: %s " % response)
            self._target_temperature = float(response['devices'][0]["CURRENT_SET_TEMPERATURE"])
            return round(self._target_temperature, 2)
        return False

    @property
    def is_away_mode_on(self):
        """ Returns if away mode is on. """
        return self._away

    def set_temperature(self, temperature):
        """ Set new target temperature. """
        _LOGGER.info("target_temp: %s" % self._target_temperature)
        _LOGGER.info("Name: %s" % self._name)
        data = {"SET_TEMP": [int(temperature), self._name]}
        json_data = json.dumps(data)
        _LOGGER.debug("set_temperature Request: %s " % json_data)
        response = self.json_request(data)
        _LOGGER.info("set_temperature response: %s " % response)

        if response:
            _LOGGER.info("response: %s " % response)
            _LOGGER.info("Target Temperature: %s " % temperature)
            # Need check for sucsess here
            # {'result': 'temperature was set'}
            self._target_temperature = temperature
            return round(self._target_temperature, 2)
        return False

    def turn_away_mode_on(self):
        """ Turns away mode on. """
        self._away = True

    def turn_away_mode_off(self):
        """ Turns away mode off. """
        self._away = False

    def update(self):
        """ Get Updated Info. """
        response = self.json_request({"INFO": "0"})
        if response:
            _LOGGER.debug("response: %s " % response)
            self._target_temperature = float(response['devices'][0]["CURRENT_SET_TEMPERATURE"])
            self._target_temperature = round(self._target_temperature, 2)
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

        _LOGGER.info("json_request: %s " % request)

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
