# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""
homeassistant.components.sensor.heatmiserneo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Heatmiser NeoStat control via Heatmiser Neo-hub
"""
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    ATTR_TEMPERATURE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)

from .const import DOMAIN, HUB
from neohubapi.neohub import NeoHub, NeoStat

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):

    hub: Neohub = hass.data[DOMAIN][HUB]
    _, devices = await hub.get_live_data()

    system_data = await hub.get_system()
    temperature_unit = system_data.CORF

    sensors = [HeatmiserNeostatFloorTemperature(hub, sensor, temperature_unit) for sensor in devices['thermostats']]

    _LOGGER.info("Adding Thermostats Sensors: %s " % sensors)
    async_add_entities(sensors, True)


class HeatmiserNeostatFloorTemperature(SensorEntity):
    """ Represents a Heatmiser Neostat thermostat floor probe. """

 def __init__(self, hub: NeoHub, neostat: NeoStat, unit_of_measurement):
        self._neostat = neostat
        self._hub = hub
        self._unit_of_measurement = unit_of_measurement
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._neostat.name} Floor Temperature"

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neostat.name}-floor"

    @property
    def state(self):
        """ Returns the floor temperature. """
        return self._neostat.current_floor_temperature
