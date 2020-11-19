"""
homeassistant.components.switch.heatmiserneo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Heatmiser NeoStat control via Heatmiser Neo-hub
JSON schema from here:
https://github.com/RJ/heatmiser-neohub.py/blob/master/neohub_docs/NeoHub%20commands%20V-2.5.pdf
"""

import logging

from homeassistant.components.switch import SwitchEntity

from .heatmiserneo import NeoHub
from .const import (DOMAIN,HUB)


_LOGGER = logging.getLogger(__package__)


NEO_STAT = 1
NEO_PLUG = 2


async def async_setup_entry(hass, entry, async_add_entities):

    hub = hass.data[DOMAIN][HUB]

    switches = []

    NeoHubJson = hub.json_request({"INFO": 0})

    _LOGGER.debug(NeoHubJson)

    for device in NeoHubJson['devices']:
        if ((device['DEVICE_TYPE'] != 6) and ('TIMECLOCK' in device['STAT_MODE'])) or (device['DEVICE_TYPE'] == 6):
            name = device['device']
            
            if (device['DEVICE_TYPE'] != 6):
                _LOGGER.info("Thermostat as Switch Named: %s " % name)
                switch_type = NEO_STAT
            else:
                _LOGGER.info("Neoplug Named: %s " % name)
                switch_type = NEO_PLUG

            switches.append(HeatmiserNeostatSwitch(hub, name, switch_type))

    _LOGGER.info("Adding Switches: %s " % switches)
    async_add_entities(switches)


class HeatmiserNeostatSwitch(SwitchEntity):
    """ Represents a Heatmiser Neostat in Switch mode. """
    def __init__(self, hub, name="Null", type=0):
        self._name = name
        self._hub = hub
        self._type = type
        self._state = None
        self._holdfor = 60
        self.update()

    @property
    def name(self):
        """ Returns the name. """
        return self._name

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return bool(self._state)

    @property
    def available(self):
        """Return true if the entity is available."""
        return True

    def turn_on(self, **kwargs):
        """ Turn the switch on. """
        if self._type == NEO_STAT:
            response = self._hub.json_request({"TIMER_HOLD_ON": [self._holdfor, self._name]})#
        elif self._type == NEO_PLUG:
            response = self._hub.json_request({"TIMER_ON": [self._name]})
        if response:
            _LOGGER.info("turn_on response: %s " % response)
            # Need check for success here

    def turn_off(self, **kwargs):
        """ Turn the switch off. """
        if self._type == NEO_STAT:
            response = self._hub.json_request({"TIMER_HOLD_OFF": [0, self._name]})
        elif self._type == NEO_PLUG:
            response = self._hub.json_request({"TIMER_OFF": [self._name]})
        if response:
            _LOGGER.info("turn_off response: %s " % response)
            # Need check for success here

    def update(self):
        """ Update the switch's status. """
        _LOGGER.debug("Entered update(self)")
        response = self._hub.json_request({"INFO": 0})
        if response:
            # Add handling for mulitple thermostats here
            _LOGGER.debug("update() json response: %s " % response)
            # self._name = device['device']
            for device in response['devices']:
                if self._name == device['device']:
                    if (device["TIMER"] == True):
                        self._state = True
                        _LOGGER.debug("On")
                    else:
                        self._state = False
                        _LOGGER.debug("Off")
        return False
