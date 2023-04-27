# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""
homeassistant.components.climate.heatmiserneo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Heatmiser NeoStat control via Heatmiser Neo-hub
"""

import logging
from typing import Optional
from abc import ABCMeta, abstractmethod

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    DEVICE_CLASS_PROBLEM,
)

from homeassistant.components.sensor import SensorEntity, DEVICE_CLASS_BATTERY

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)

from neohubapi.neohub import NeoHub, NeoStat
from .const import DOMAIN, HUB, COORDINATOR

_LOGGER = logging.getLogger(__name__)

THERMOSTATS = "thermostats"
ICON_BATTERY_LOW = "mdi:battery-low"
ICON_BATTERY_OFF = "mdi:battery-off"
ICON_BATTERY_FULL = "mdi:battery"
ICON_NETWORK_OFFLINE = "mdi:network-off-outline"
ICON_NETOWRK_ONLINE = "mdi:network-outline"


async def async_setup_entry(hass, entry, async_add_entities):
    # hub: NeoHub = hass.data[DOMAIN][HUB]
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][COORDINATOR]

    (devices_data, system_data) = coordinator.data
    thermostats = {device.name: device for device in devices_data[THERMOSTATS]}

    battery_level_sensors = []
    offline_binary_sensors = []

    for thermostat in thermostats.values():
        battery_level_sensors.append(NeoStatBatterySensor(thermostat, coordinator))
        offline_binary_sensors.append(
            NeoStatOfflineBinarySensor(thermostat, coordinator)
        )

    _LOGGER.info(
        f"Adding Thermostat Low Battery Binary Sensors: {battery_level_sensors}"
    )
    async_add_entities(battery_level_sensors, True)
    _LOGGER.info(f"Adding Thermostat Offline Binary Sensors: {offline_binary_sensors}")
    async_add_entities(offline_binary_sensors, True)


class NeoStatBatterySensor(CoordinatorEntity, SensorEntity):
    """Represents the battery status of the thermostaat"""

    def __init__(self, neostat: NeoStat, coordinator: DataUpdateCoordinator):
        super().__init__(coordinator)
        _LOGGER.debug(f"Creating {type(self).__name__} for {neostat.name}")

        self._neostat = neostat
        self._coordinator = coordinator

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        thermostats = {device.name: device for device in devices[THERMOSTATS]}
        return thermostats[self._neostat.name]

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._neostat.name} Battery Level Sensor"

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neostat.device_id}_battery_level"

    @property
    def native_unit_of_measurement(self):
        """Return the percentage"""
        return "%"

    @property
    def native_value(self):
        """Return the battery value in percentage."""
        if self.data.offline:
            return 0
        if self.data.low_battery:
            return 10

        return 100

    @property
    def device_class(self):
        return DEVICE_CLASS_BATTERY

    @property
    def icon(self):
        if self.data.offline:
            return ICON_BATTERY_OFF
        if self.data.low_battery:
            return ICON_BATTERY_LOW

        return ICON_BATTERY_FULL

    @property
    def device_info(self):
        return {
            "identifiers": {("heatmiser neoStat", self._neostat.name)},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": "neoStat",
            "suggested_area": self._neostat.name,
        }


class NeoStatOfflineBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Represents a Heatmiser Neostat offline binary sensor"""

    def __init__(self, neostat: NeoStat, coordinator: DataUpdateCoordinator):
        super().__init__(coordinator)
        _LOGGER.debug(f"Creating {type(self).__name__} for {neostat.name}")

        self._neostat = neostat
        self._coordinator = coordinator

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        thermostats = {device.name: device for device in devices[THERMOSTATS]}
        return thermostats[self._neostat.name]

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._neostat.name} Offline Binary Sensor"

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def available(self):
        """Return true if the entity is available."""
        return True

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neostat.device_id}_offline"

    @property
    def is_on(self):
        """Return true if the binary sensor is on. i.e. NeoStat is offline"""
        return bool(self.data.offline)

    @property
    def device_class(self):
        return DEVICE_CLASS_PROBLEM

    @property
    def icon(self):
        if self.data.offline:
            return ICON_NETWORK_OFFLINE

        return ICON_NETOWRK_ONLINE

    @property
    def device_info(self):
        return {
            "identifiers": {("heatmiser neoStat", self._neostat.name)},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": "neoStat",
            "suggested_area": self._neostat.name,
        }
