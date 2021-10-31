# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""
homeassistant.components.sensor.heatmiserneo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Heatmiser NeoStat control via Heatmiser Neo-hub
"""

import logging

from homeassistant.helpers.config_validation import temperature_unit
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    TEMPERATURE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)

from neohubapi.neohub import NeoHub, NeoStat
from .const import DOMAIN, HUB

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):

    hub = hass.data[DOMAIN][HUB]
    _, devices = await hub.get_live_data()

    system_data = await hub.get_system()
    temperature_unit = system_data.CORF

    sensors = [
        HeatmiserNeostatFloorTemperature(hub, sensor, temperature_unit)
        for sensor in devices["thermostats"] if sensor.current_floor_temperature < 127  # Exclude device if floor temperature is 127 or higher (V1 of the NeoStat reports 127 when no probe is connected, V2 reports 127.5)
    ]

    _LOGGER.info("Adding Thermostats Sensors: %s " % sensors)
    async_add_entities(sensors, True)


class HeatmiserNeostatFloorTemperature(SensorEntity):
    """Represents a Heatmiser Neostat thermostat floor probe."""

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
        return f"{self._neostat.device_id}-floor-sensor"

    @property
    def state(self):
        """Returns the floor temperature."""
        return self._state

    @property
    def entity_registry_enabled_default(self):
        """Disable entity if value is above 127 (V1 of the NeoStat reports 127 when no probe is connected, V2 reports 127.5)"""
        return self.state < 127

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        if self._unit_of_measurement == "C":
            return TEMP_CELSIUS
        if self._unit_of_measurement == "F":
            return TEMP_FAHRENHEIT
        return self._unit_of_measurement

    @property
    def device_info(self):
        """Device Registation"""
        return {
            "identifiers": {("HeatMiser NeoStat", self._neostat.name)},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": "NeoStat",
            "suggested_area": self._neostat.name,
        }

    @property
    def device_class(self):
        return TEMPERATURE

    async def async_update(self):
        """Update the sensor's status."""
        _LOGGER.debug("Entered sensor.update(self)")
        _, devices = await self._hub.get_live_data()
        for sensor in devices["thermostats"]:
            if self._neostat.name == sensor.name:
                self._state = sensor.current_floor_temperature
 
