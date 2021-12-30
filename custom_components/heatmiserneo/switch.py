
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
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from neohubapi.neohub import NeoHub, NeoStat
from .const import DOMAIN, HUB, COORDINATOR

_LOGGER = logging.getLogger(__name__)


NEO_STAT = 1
NEO_PLUG = 2
TIMECLOCKS = 'timeclocks'

async def async_setup_entry(hass, entry, async_add_entities):
    
    hub: NeoHub = hass.data[DOMAIN][HUB]
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][COORDINATOR]

    (devices_data, system_data) = coordinator.data
    timers = {device.name : device for device in devices_data[TIMECLOCKS]}
    
    entities = [NeoTimerEntity(timer, coordinator, NEO_STAT) for timer in timers.values()]
    
    _LOGGER.info(f"Adding Timers: {entities}")
    async_add_entities(entities, True)
    
class NeoTimerEntity(CoordinatorEntity, SwitchEntity):
    """ Represents a Heatmiser neoStat thermostat. """
    def __init__(self, timer: NeoStat, coordinator: DataUpdateCoordinator, type):
        super().__init__(coordinator)
        _LOGGER.debug(f"Creating {timer}")
        
        self._timer = timer
        self._coordinator = coordinator
        self._type = type
        self._state = timer.timer_on
        self._holdfor = 30

    @property
    def data(self):
        """Helper to get the data for the current thermostat. """
        (devices, _) = self._coordinator.data
        timers = {device.name : device for device in devices[TIMECLOCKS]}
        return timers[self.name]
        
    @property
    def should_poll(self):
        """ Don't poll - we fetch the data from the hub all at once """
        return False
        
    @property
    def name(self):
        """ Returns the name. """
        return self._timer.name

    @property
    def unique_id(self):
        """Return a unique ID"""
        return self._timer.name

    @property
    def state(self):
        """Return the entity state."""
        return 'on' if self.data.timer_on else 'off'
        
    @property
    def is_on(self):
        """Return true if the switch is on."""
        return bool(self._state)

    @property
    def available(self):
        """Return true if the entity is available."""
        return True
    
    @property
    def device_info(self):
        return {
            "identifiers": {("heatmiser neoStat", self._timer.name)},
            "name": self._timer.name,
            "manufacturer": "Heatmiser",
            "model": "neoTimer",
            "suggested_area": self._timer.name,
        }
    
    async def async_turn_on(self, **kwargs):
        """ Turn the switch on. """
        _LOGGER.info(f"{self.name} : Executing turn_on() with: {kwargs}")
        
        await self.async_switch_on(True)
        
    async def async_turn_off(self, **kwargs):
        """ Turn the switch off. """
        _LOGGER.info(f"{self.name} : Executing turn_off() with: {kwargs}")
        
        await self.async_switch_on(False)

    async def async_switch_on(self, value: bool):
        if self._type == NEO_STAT:
            response = await self._timer.set_timer_hold(value, self._holdfor if value else 0)
            _LOGGER.info(f"{self.name} : Called set_timer_hold with: {value} (response: {response})")
            self.data.timer_on = value
            self.async_write_ha_state()
            
        elif self._type == NEO_PLUG:
            response = await self._hub.set_timer(value, [self])
