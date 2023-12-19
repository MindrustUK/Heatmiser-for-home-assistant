# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""
homeassistant.components.sensor.heatmiserneo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Heatmiser Neo Sensors via Heatmiser Neo-hub
"""

import logging    

_LOGGER = logging.getLogger(__name__)

from .const import COORDINATOR, DOMAIN, HUB, HEATMISER_PRODUCT_LIST
from neohubapi.neohub import NeoHub, NeoStat
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity

SENSORS_ENABLED = True
OFFLINE_SENSOR_ENABLED = True
ICON_BATTERY_LOW = "mdi:battery-low"
ICON_BATTERY_OFF = "mdi:battery-off"
ICON_BATTERY_FULL = "mdi:battery"
ICON_NETWORK_OFFLINE = "mdi:network-off-outline"
ICON_NETWORK_ONLINE = "mdi:network-outline"


async def async_setup_entry(hass, entry, async_add_entities):
    hub: NeoHub = hass.data[DOMAIN][HUB]
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][COORDINATOR]

    (devices_data, system_data) = coordinator.data

    temperature_unit = system_data.CORF

    if SENSORS_ENABLED:  # Todo: Placeholder, move this to Hub configuration
        neo_devices = {device.name: device for device in devices_data['neo_devices']}
        _LOGGER.debug(f"Heatmiser Neo Devices: {neo_devices}")

        # Todo: Add all devices, Thermostats, timeclocks the lot.
        list_of_neo_devices = []

        for neo_device in neo_devices.values():
            # Sensor has a binary sensing element (Window Door Sensor)
            if neo_device.device_type == 5:
                list_of_neo_devices.append(HeatmiserNeoContactSensor(neo_device, coordinator, hub))

            if neo_device.device_type in [1, 6, 12]:
                list_of_neo_devices.append(HeatmiserNeoHoldTimeSensor(neo_device, coordinator, hub))
                list_of_neo_devices.append(HeatmiserNeoHoldActiveSensor(neo_device, coordinator))

            # Thermostats in Time Clock mode
            if (neo_device.device_type in [1, 12]) and neo_device.time_clock_mode:
                list_of_neo_devices.append(HeatmiserNeoTimerOutputActiveSensor(neo_device, coordinator))
            
            # Sensor has a temperature sensing element
            if neo_device.device_type == 14:
                list_of_neo_devices.append(
                    HeatmiserNeoTemperatureSensor(neo_device, coordinator, hub, temperature_unit))

            # Is the device battery powered?
            if neo_device.battery_powered:
                list_of_neo_devices.append(NeoBatterySensor(neo_device, coordinator))

            # TODO: Move this to configuration.
            if OFFLINE_SENSOR_ENABLED:
                list_of_neo_devices.append(NeoOfflineBinarySensor(neo_device, coordinator))

        _LOGGER.info(f"Adding Sensors: {list_of_neo_devices}")
        async_add_entities(list_of_neo_devices, True)


class NeoOfflineBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Represents a Heatmiser Neostat offline binary sensor"""

    def __init__(self, neosensor: NeoStat, coordinator: DataUpdateCoordinator):
        super().__init__(coordinator)
        _LOGGER.debug(f"Creating {type(self).__name__} for Device ID: {neosensor.device_id} Name: {neosensor.name}")

        self._neosensor = neosensor
        self._coordinator = coordinator

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        thermostats = {device.name: device for device in devices['neo_devices']}
        return thermostats[self._neosensor.name]

    @property
    def device_class(self):
        return BinarySensorDeviceClass.CONNECTIVITY

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._neosensor.name} Heatmiser {HEATMISER_PRODUCT_LIST[self._neosensor.device_type]} Device Connectivity"

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def available(self):
        """Return true if the entity is available."""
        # This has to always be available otherwise it will never work.
        return True

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neosensor.device_id}_device_offline_sensor"

    @property
    def is_on(self):
        """Return true if the binary sensor is on. i.e. Neo Device is offline"""
        return not bool(self.data.offline)

    @property
    def icon(self):
        if self.data.offline:
            return ICON_NETWORK_OFFLINE

        return ICON_NETWORK_ONLINE

    @property
    def device_info(self):
        return {
            "identifiers": {("Heatmiser Neo Device", self._neosensor.device_id)},
            "name": self._neosensor.name,
            "manufacturer": "Heatmiser",
            "suggested_area": self._neosensor.name
        }


class HeatmiserNeoContactSensor(CoordinatorEntity, BinarySensorEntity):
    """Represents a Heatmiser Neostat Contact Sensor"""

    def __init__(
            self,
            neosensor: NeoStat,
            coordinator: DataUpdateCoordinator,
            hub: NeoHub
    ):
        super().__init__(coordinator)
        _LOGGER.debug(f"Creating {type(self).__name__} for Device ID: {neosensor.device_id} Name: {neosensor.name}")

        self._neosensor = neosensor
        self._coordinator = coordinator
        self._hub = hub

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        contact_sensors = {device.name: device for device in devices['neo_devices']}
        return contact_sensors[self._neosensor.name]

    @property
    def available(self):
        """Return true if the entity is available."""
        if self.data.offline:
            return False
        return True

    @property
    def device_class(self):
        return BinarySensorDeviceClass.OPENING

    @property
    def device_info(self):
        return {
            "identifiers": {("Heatmiser Neo Device", self._neosensor.device_id)},
            "name": self._neosensor.name,
            "manufacturer": "Heatmiser",
            "model": f"Contact Sensor - Device Type: {self._neosensor.device_type}",
            "suggested_area": self._neosensor.name,
            "sw_version": self._neosensor.stat_version,
            "via_device": self._hub
        }

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        attributes = {
            'device_id': self._neosensor.device_id,
            'device_type': self._neosensor.device_type,
            'low_battery': self.data.low_battery,
            'offline': self.data.offline
        }
        return attributes

    @property
    def icon(self):
        if self.data.offline:
            return "mdi:network-off-outline"

        if self.data.window_open:
            return "mdi:electric-switch"

        if not self.data.window_open:
            return "mdi:electric-switch-closed"

        return "mdi:image-broken-variant"

    @property
    def is_on(self):
        """Return true if the binary sensor is on. i.e. Contacts are open"""
        return bool(self.data.window_open)

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._neosensor.name} Heatmiser {HEATMISER_PRODUCT_LIST[self._neosensor.device_type]} Contact Sensor"

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neosensor.device_id}_contact_sensor"


class HeatmiserNeoHoldActiveSensor(CoordinatorEntity, BinarySensorEntity):
    """Represents a Heatmiser Neostat offline binary sensor"""

    def __init__(self, neostat: NeoStat, coordinator: DataUpdateCoordinator):
        super().__init__(coordinator)
        _LOGGER.debug(f"Creating {type(self).__name__} for Device ID: {neostat.device_id} Name: {neostat.name}")

        self._neostat = neostat
        self._coordinator = coordinator

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        thermostats = {device.name: device for device in devices['neo_devices']}
        return thermostats[self._neostat.name]

    @property
    def device_class(self):
        return BinarySensorDeviceClass.NONE

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._neostat.name} Heatmiser {HEATMISER_PRODUCT_LIST[self._neostat.device_type]} Hold Active"

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def available(self):
        """Return true if the entity is available."""
        if self.data.offline:
            return False
        return True

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neostat.device_id}_device_hold_active"

    @property
    def is_on(self):
        """Return true if the binary sensor is on. i.e. Neo Device is offline"""
        return bool(self.data.hold_on)

    @property
    def device_class(self):
        return BinarySensorDeviceClass.PROBLEM

    @property
    def device_info(self):
        return {
            "identifiers": {("Heatmiser Neo Device", self._neostat.device_id)},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "suggested_area": self._neostat.name
        }


class HeatmiserNeoHoldTimeSensor(CoordinatorEntity, SensorEntity):
    """Represents A Heatmiser Device with a Hold Time"""

    def __init__(
            self,
            neostat: NeoStat,
            coordinator: DataUpdateCoordinator,
            hub: NeoHub
    ):
        super().__init__(coordinator)
        _LOGGER.debug(f"Creating {type(self).__name__} for Device ID: {neostat.device_id} Name: {neostat.name}")

        self._neostat = neostat
        self._coordinator = coordinator
        self._hub = hub

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        temperature_sensors = {device.name: device for device in devices['neo_devices']}
        return temperature_sensors[self._neostat.name]

    @property
    def available(self):
        """Return true if the entity is available."""
        if self.data.offline:
            return False
        return True

    @property
    def device_class(self):
        return None

    @property
    def device_info(self):
        return {
            "identifiers": {("Heatmiser Neo Device", self._neostat.device_id)},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "suggested_area": self._neostat.name
        }

    @property
    def extra_state_attributes(self):
        """Return the additional state attributes."""
        attributes = {
            'device_id': self._neostat.device_id,
            'device_type': self._neostat.device_type,
            'offline': self.data.offline
        }
        return attributes
        
    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._neostat.name} Heatmiser {HEATMISER_PRODUCT_LIST[self._neostat.device_type]} Hold Time Remaining"

    @property
    def native_value(self):
        """Return the sensors temperature value."""
        if self.data.offline:
            return None
        return self.data.hold_time

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neostat.device_id}_hold_time_sensor"


class NeoBatterySensor(CoordinatorEntity, BinarySensorEntity):
    """Represents the battery status of the thermostat"""

    def __init__(self, neosensor: NeoStat, coordinator: DataUpdateCoordinator):
        super().__init__(coordinator)
        _LOGGER.debug(f"Creating {type(self).__name__} for Device ID: {neosensor.device_id} Name: {neosensor.name}")

        self._neosensor = neosensor
        self._coordinator = coordinator

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        thermostats = {device.name: device for device in devices['neo_devices']}
        return thermostats[self._neosensor.name]

    @property
    def available(self):
        """Return true if the entity is available."""
        if self.data.offline:
            return False
        return True

    @property
    def device_class(self):
        return BinarySensorDeviceClass.BATTERY

    @property
    def device_info(self):
        return {
            "identifiers": {("Heatmiser Neo Device", self._neosensor.device_id)},
            "name": self._neosensor.name,
            "manufacturer": "Heatmiser",
            "model": f"Device Type: {self._neosensor.device_type}",
            "suggested_area": self._neosensor.name,
            "sw_version": self.data.stat_version
        }

    @property
    def is_on(self):
        """Return true if the binary sensor is on. i.e. Contacts are open"""
        return bool(self.data.low_battery)

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._neosensor.name} Heatmiser {HEATMISER_PRODUCT_LIST[self._neosensor.device_type]} Battery Low"

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neosensor.device_id}_battery_level_sensor"


class HeatmiserNeoTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Represents A Heatmiser Temperature Sensor"""

    def __init__(
            self,
            neosensor: NeoStat,
            coordinator: DataUpdateCoordinator,
            hub: NeoHub,
            unit_of_measurement
    ):
        super().__init__(coordinator)
        _LOGGER.debug(f"Creating {type(self).__name__} for Device ID: {neosensor.device_id} Name: {neosensor.name}")

        self._neosensor = neosensor
        self._coordinator = coordinator
        self._hub = hub
        self._unit_of_measurement = unit_of_measurement

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        temperature_sensors = {device.name: device for device in devices['neo_devices']}
        return temperature_sensors[self._neosensor.name]

    @property
    def available(self):
        """Return true if the entity is available."""
        if self.data.offline:
            return False
        return True

    @property
    def device_class(self):
        return SensorDeviceClass.TEMPERATURE

    @property
    def device_info(self):
        return {
            "identifiers": {("Heatmiser Neo Device", self._neosensor.device_id)},
            "name": self._neosensor.name,
            "manufacturer": "Heatmiser",
            "model": f"Wireless Air Sensor - Device Type: {self._neosensor.device_type}",
            "suggested_area": self._neosensor.name,
            "sw_version": self._neosensor.stat_version,
            "via_device": self._hub
        }

    @property
    def extra_state_attributes(self):
        """Return the additional state attributes."""
        attributes = {
            'device_id': self._neosensor.device_id,
            'device_type': self._neosensor.device_type,
            'low_battery': self.data.low_battery,
            'offline': self.data.offline
        }
        return attributes

    @property
    def icon(self):
        if self.data.offline:
            return "mdi:thermometer-alert"
        return "mdi:thermometer-auto"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._neosensor.name} Heatmiser {HEATMISER_PRODUCT_LIST[self._neosensor.device_type]} Temperature"

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        if self.data.offline:
            return None
        elif self._unit_of_measurement == "C":
            return "°C"
        elif self._unit_of_measurement == "F":
            return "°F"
        else:
            return None

    @property
    def native_value(self):
        """Return the sensors temperature value."""
        if self.data.offline:
            return None
        return float(self.data.temperature)

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neosensor.device_id}_temperature_sensor"


class HeatmiserNeoTimerOutputActiveSensor(CoordinatorEntity, BinarySensorEntity):
    """Represents a Heatmiser Neostat Timer Output Active binary sensor"""

    def __init__(self, neostat: NeoStat, coordinator: DataUpdateCoordinator):
        super().__init__(coordinator)
        _LOGGER.debug(f"Creating {type(self).__name__} for Device ID: {neostat.device_id} Name: {neostat.name}")

        self._neostat = neostat
        self._coordinator = coordinator

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        thermostats = {device.name: device for device in devices['neo_devices']}
        return thermostats[self._neostat.name]

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._neostat.name} Heatmiser {HEATMISER_PRODUCT_LIST[self._neostat.device_type]} Timer Output Active"

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def available(self):
        """Return true if the entity is available."""
        if self.data.offline:
            return False
        return True

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neostat.device_id}_device_timer_output_active"

    @property
    def is_on(self):
        """Return true if the binary sensor is on. i.e. Neo Device is timer output is active"""
        return bool(self.data.timer_on)

    @property
    def device_info(self):
        return {
            "identifiers": {("Heatmiser Neo Device", self._neostat.device_id)},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "suggested_area": self._neostat.name
        }

