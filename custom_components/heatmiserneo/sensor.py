
# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""
homeassistant.components.climate.heatmiserneo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Heatmiser NeoStat control via Heatmiser Neo-hub
"""

import logging
from typing import Optional

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_PROBLEM
)

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator
)

from neohubapi.neohub import NeoHub, NeoStat
from .const import DOMAIN, HUB, COORDINATOR

_LOGGER = logging.getLogger(__name__)

THERMOSTATS = 'thermostats'
LOW_BATTERY_ICON = "mdi:battery-low"
OFFLINE_ICON = "mdi:battery-remove-outline"


async def async_setup_entry(hass, entry, async_add_entities):

    hub: NeoHub = hass.data[DOMAIN][HUB]
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][COORDINATOR]

    (devices_data, system_data) = coordinator.data
    thermostats = {device.name: device for device in devices_data[THERMOSTATS]}

    low_battery_binary_sensors = [NeoStatLowBatteryBinarySensor(thermostat) for thermostat in
                                  thermostats.values()]
    offline_binary_sensors = [NeoStatOfflineBinarySensor(thermostat) for thermostat in
                              thermostats.values()]

    _LOGGER.info(f"Adding Thermostat Low Battery Binary Sensors: {low_battery_binary_sensors}")
    async_add_entities(low_battery_binary_sensors, True)
    _LOGGER.info(f"Adding Thermostat Offline Binary Sensors: {offline_binary_sensors}")
    async_add_entities(offline_binary_sensors, True)


class NeoStatLowBatteryBinarySensor(BinarySensorEntity):
    """ Represents a Heatmiser Neostat low battery binary sensor """
    def __init__(self, neostat: NeoStat):
        _LOGGER.debug(f"Creating low battery binary sensor for {neostat.name}")

        self._neostat = neostat

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._neostat.name} Low Battery Binary Sensor"

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neostat.device_id}_low_battery"

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if the binary sensor is on."""
        return self._neostat.low_battery

    @property
    def device_class(self):
        return DEVICE_CLASS_BATTERY

    @property
    def icon(self):
        return LOW_BATTERY_ICON

    @property
    def device_info(self):
        return {
            "identifiers": {("heatmiser neoStat", self._neostat.name)},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": "neoStat",
            "suggested_area": self._neostat.name,
        }


class NeoStatOfflineBinarySensor(BinarySensorEntity):
    """ Represents a Heatmiser Neostat offline binary sensor """
    def __init__(self, neostat: NeoStat):
        _LOGGER.debug(f"Creating offline binary sensor for {neostat.name}")

        self._neostat = neostat

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._neostat.name} Offline Binary Sensor"

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neostat.device_id}_offline"

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if the binary sensor is on."""
        return self._neostat.offline

    @property
    def device_class(self):
        return DEVICE_CLASS_PROBLEM

    @property
    def icon(self):
        return OFFLINE_ICON

    @property
    def device_info(self):
        return {
            "identifiers": {("heatmiser neoStat", self._neostat.name)},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": "neoStat",
            "suggested_area": self._neostat.name,
        }
