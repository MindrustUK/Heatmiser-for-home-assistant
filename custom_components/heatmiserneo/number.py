import logging

from homeassistant.components.number import NumberEntity, NumberMode

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)

from neohubapi.neohub import NeoHub, NeoStat
from .const import COORDINATOR, DOMAIN, HUB, HEATMISER_PRODUCT_LIST

_LOGGER = logging.getLogger(__name__)

HOLD_CONTROLS_ENABLED = True


async def async_setup_entry(hass, entry, async_add_entities):
    hub: NeoHub = hass.data[DOMAIN][HUB]
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][COORDINATOR]

    (devices_data, system_data) = coordinator.data

    thermostats = {device.name: device for device in devices_data['neo_devices']}
    list_of_thermostat_buttons = []

    for thermostat in thermostats.values():
        if HOLD_CONTROLS_ENABLED:
            # All Thermostats, Thermostats operating in Timeclock Mode and Neoplugs can have Hold times.
            if thermostat.device_type in [1, 2, 6, 7, 12, 13]:
                list_of_thermostat_buttons.append(HoldHours(thermostat, coordinator, hub))
                list_of_thermostat_buttons.append(HoldMins(thermostat, coordinator, hub))

                if (thermostat.device_type in [1, 2, 7, 12, 13]) and (thermostat.time_clock_mode == False):
                    list_of_thermostat_buttons.append(TargetTemperature(thermostat, coordinator, hub))

    _LOGGER.info(f"Adding Thermostat Buttons: {list_of_thermostat_buttons}")
    async_add_entities(list_of_thermostat_buttons, True)


class HoldHours(CoordinatorEntity, NumberEntity):
    """Number input field for Hold Hours"""

    def __init__(
            self,
            neostat: NeoStat,
            coordinator: DataUpdateCoordinator,
            hub: NeoHub
    ):
        super().__init__(coordinator)
        _LOGGER.debug(f"Creating {type(self).__name__} for {neostat.name}")

        self._neostat = neostat
        self._coordinator = coordinator
        self._hub = hub
        self._attr_native_value = self._neostat.hold_hours

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        thermostats = {device.name: device for device in devices['neo_devices']}
        return thermostats[self._neostat.name]

    @property
    def available(self):
        """Return true if the entity is available."""
        if self.data.offline:
            return False
        return True

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._coordinator.serial_number}_{self._neostat.serial_number}")},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "serial_number": self._neostat.serial_number,
            "suggested_area": self._neostat.name,
            "via_device": (DOMAIN, self._coordinator.serial_number),
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
    def mode(self):
        """ Returns the name. """
        return NumberMode.BOX

    @property
    def name(self):
        """ Returns the name. """
        return f"{self._neostat.name} Heatmiser {HEATMISER_PRODUCT_LIST[self._neostat.device_type]} Hold time Hours"

    @property
    def native_value(self):
        """ Returns the name. """
        return self.data.hold_hours

    @property
    def native_max_value(self):
        """ Returns the name. """
        return 99

    @property
    def native_mix_value(self):
        """ Returns the name. """
        return 0

    async def async_set_native_value(self, value: int):
        """Update the current value."""
        self._neostat.hold_hours = value

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def unique_id(self):
        """Return a unique ID"""
        # Use both the Hub and Device serial numbers as you can have orphaned devices still present in hub configuration.
        return f"{self._neostat.name}_{self._coordinator.serial_number}_{self._neostat.serial_number}_heatmiser_neo_hold_time_hours"


class HoldMins(CoordinatorEntity, NumberEntity):
    """Number input field for Hold Minutes"""

    def __init__(
            self,
            neostat: NeoStat,
            coordinator: DataUpdateCoordinator,
            hub: NeoHub
    ):
        super().__init__(coordinator)
        _LOGGER.debug(f"Creating {type(self).__name__} for {neostat.name}")

        self._neostat = neostat
        self._coordinator = coordinator
        self._hub = hub
        self._attr_native_value = self._neostat.hold_mins

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        thermostats = {device.name: device for device in devices['neo_devices']}
        return thermostats[self._neostat.name]

    @property
    def available(self):
        """Return true if the entity is available."""
        if self.data.offline:
            return False
        return True

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._coordinator.serial_number}_{self._neostat.serial_number}")},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "serial_number": self._neostat.serial_number,
            "suggested_area": self._neostat.name,
            "via_device": (DOMAIN, self._coordinator.serial_number),
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
    def mode(self):
        """ Returns the name. """
        return NumberMode.BOX

    @property
    def name(self):
        """ Returns the name. """
        return f"{self._neostat.name} Heatmiser {HEATMISER_PRODUCT_LIST[self._neostat.device_type]} Hold Time Minutes"

    @property
    def native_value(self):
        """ Returns the name. """
        return self.data.hold_mins

    @property
    def native_max_value(self):
        """ Returns the name. """
        return 59

    @property
    def native_mix_value(self):
        """ Returns the name. """
        return 0

    async def async_set_native_value(self, value: int):
        """Update the current value."""
        # Todo: Make this a local variable.
        self._neostat.hold_mins = value

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def unique_id(self):
        """Return a unique ID"""
        # Use both the Hub and Device serial numbers as you can have orphaned devices still present in hub configuration.
        return f"{self._neostat.name}_{self._coordinator.serial_number}_{self._neostat.serial_number}_heatmiser_neo_hold_time_mins"


class TargetTemperature(CoordinatorEntity, NumberEntity):
    """Number input field for Hold Target Temperature"""

    def __init__(
            self,
            neostat: NeoStat,
            coordinator: DataUpdateCoordinator,
            hub: NeoHub
    ):
        super().__init__(coordinator)
        _LOGGER.debug(f"Creating {type(self).__name__} for {neostat.name} {neostat.device_id}")

        self._neostat = neostat
        self._coordinator = coordinator
        self._hub = hub
        self._attr_native_value = self._neostat.hold_temp

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        thermostats = {device.name: device for device in devices['neo_devices']}
        return thermostats[self._neostat.name]

    @property
    def available(self):
        """Return true if the entity is available."""
        if self.data.offline:
            return False
        return True

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._coordinator.serial_number}_{self._neostat.serial_number}")},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "serial_number": self._neostat.serial_number,
            "suggested_area": self._neostat.name,
            "via_device": (DOMAIN, self._coordinator.serial_number),
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
    def mode(self):
        """ Returns the name. """
        return NumberMode.BOX

    @property
    def name(self):
        """ Returns the name. """
        return f"{self._neostat.name} Heatmiser {HEATMISER_PRODUCT_LIST[self._neostat.device_type]} Hold Target Temperature"

    @property
    def native_max_value(self):
        """ Returns the Maximum value. """
        return self._neostat.max_temperature_limit

    @property
    def native_mix_value(self):
        """ Returns the name. """
        return self._neostat.min_temperature_limit

    @property
    def native_value(self):
        """ Returns the name. """
        return self._neostat.hold_temp

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        # Todo: Make this a local variable.
        self._neostat.hold_temp = value

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def unique_id(self):
        """Return a unique ID"""
        # Use both the Hub and Device serial numbers as you can have orphaned devices still present in hub configuration.
        return f"{self._neostat.name}_{self._coordinator.serial_number}_{self._neostat.serial_number}_heatmiser_neo_hold_target_temp"
  
