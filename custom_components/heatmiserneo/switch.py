
# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""
homeassistant.components.switch.heatmiserneo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Heatmiser NeoStat control via Heatmiser Neo-hub
JSON schema from here:
https://github.com/RJ/heatmiser-neohub.py/blob/master/neohub_docs/NeoHub%20commands%20V-2.5.pdf
"""

import logging

from homeassistant.components.switch import SwitchEntity

from neohubapi.neohub import NeoHub
from .const import DOMAIN, HUB


_LOGGER = logging.getLogger(__name__)


NEO_STAT = 1
NEO_PLUG = 2


async def async_setup_entry(hass, entry, async_add_entities):

    hub = hass.data[DOMAIN][HUB]
    _, devices = await hub.get_live_data()

    switches = []
    # FIXME: handle NEO_PLUG with DEVICE_TYPE == 6, needs support in neohubapi
    switches = [HeatmiserNeostatSwitch(hub, switch, NEO_STAT) for switch in devices['timeclocks']]

    _LOGGER.info("Adding Switches: %s " % switches)
    async_add_entities(switches, True)


class HeatmiserNeostatSwitch(SwitchEntity):
    """ Represents a Heatmiser Neostat in Switch mode. """
    def __init__(self, hub: NeoHub, switch, type=0):
        self._switch = switch
        self._hub = hub
        self._type = type
        self._state = None
        self._holdfor = 60

    @property
    def name(self):
        """ Returns the name. """
        return self._switch.name

    @property
    def unique_id(self):
        """Return a unique ID"""
        return self._switch.name

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return bool(self._state)

    @property
    def available(self):
        """Return true if the entity is available."""
        return True

    async def async_turn_on(self, **kwargs):
        """ Turn the switch on. """
        if self._type == NEO_STAT:
            response = await self._switch.set_timer_hold(True, self._holdfor)
        elif self._type == NEO_PLUG:
            response = await self._hub.set_timer(True, [self])

    async def async_turn_off(self, **kwargs):
        """ Turn the switch off. """
        if self._type == NEO_STAT:
            response = await self._switch.set_timer_hold(False, 0)
        elif self._type == NEO_PLUG:
            response = await self._hub.set_timer(False, [self])

    async def async_update(self):
        """ Update the switch's status. """
        _LOGGER.debug("Entered switch.update(self)")
        _, devices = await self._hub.get_live_data()
        for device in devices['timeclocks']:
            if self._switch.name == device.name:
                self._state = device.timer_on
