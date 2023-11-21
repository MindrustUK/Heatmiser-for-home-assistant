# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""
homeassistant.components.switch.heatmiserneo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from datetime import time
import logging

from homeassistant.const import EntityCategory
from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from neohubapi.neohub import NeoHub, NeoStat
from .const import COORDINATOR, DOMAIN, HUB, HEATMISER_PRODUCT_LIST

_LOGGER = logging.getLogger(__name__)

DEVICES_ENABLED_NEO_PLUG = True
HOLD_CONTROLS_ENABLED = True


async def async_setup_entry(hass, entry, async_add_entities):
    hub: NeoHub = hass.data[DOMAIN][HUB]
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][COORDINATOR]

    (devices_data, system_data) = coordinator.data

    neo_devices = {device.name: device for device in devices_data["neo_devices"]}
    _LOGGER.info(f"neo_devices: {neo_devices}")
    list_of_neo_devices = []
    for neo_device in neo_devices.values():
        # Only Heatmiser Neo Plugs support manual switching and disabling timers.
        if DEVICES_ENABLED_NEO_PLUG:
            if neo_device.device_type == 6:
                list_of_neo_devices.append(HeatmiserNeoPlugPowerSwitch(neo_device, coordinator, hub))
                list_of_neo_devices.append(HeatmiserNeoPlugTimerSwitch(neo_device, coordinator, hub))
                # TODO: Restore Timer switch goes here as config option.
                # list_of_neo_devices.append(HeatmiserNeoPlugTimerSwitch(neo_device, coordinator, hub))

        if HOLD_CONTROLS_ENABLED:
            # TODO: Check if Hold Controls should be displayed, check config for this.
            # Thermostats (In Thermostat / Timeclock mode) and NeoPlugs all allow for holding.

            # Thermostats not operating in time clock mode should have the Hold Temperature switch.
            if (neo_device.device_type in [1, 12]) and (not neo_device.time_clock_mode):
                list_of_neo_devices.append(HeatmiserTemperatureHoldSwitch(neo_device, coordinator, hub))

            # Neo plugs and Thermostats in Time Clock mode
            if (neo_device.device_type in [1, 12]) and neo_device.time_clock_mode:
                # Switch to control hold active
                list_of_neo_devices.append(HeatmiserTimerHoldSwitch(neo_device, coordinator, hub))
                # Switch to control hold state, hold_on vs hold_off
                list_of_neo_devices.append(HeatmiserTimerHoldStateSwitch(neo_device, coordinator, hub))

            # Neo plugs always get hold controls
            if neo_device.device_type == 6:
                list_of_neo_devices.append(HeatmiserTimerHoldSwitch(neo_device, coordinator, hub))
                list_of_neo_devices.append(HeatmiserTimerHoldStateSwitch(neo_device, coordinator, hub))

    _LOGGER.info(f"Adding neoPlug switches: {list_of_neo_devices}")
    async_add_entities(list_of_neo_devices, True)


class HeatmiserNeoPlugPowerSwitch(CoordinatorEntity, SwitchEntity):
    """Represents a Heatmiser Neo Plug"""

    """Handles:
    {"TIMER_ON":"plug"} TIMER_ON turns the output on
    {"TIMER_OFF":"plug"} TIMER_OFF turns the output off
    """

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
        self._state = neostat.timer_on

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        neo_devices = {device.name: device for device in devices["neo_devices"]}
        return neo_devices[self._neostat.name]

    @property
    def available(self):
        """Return true if the entity is available."""
        if self.data.offline:
            return False
        else:
            return True

    @property
    def device_class(self):
        return SwitchDeviceClass.OUTLET

    @property
    def device_info(self):
        return {
            "identifiers": {("Heatmiser Neo Device", self._neostat.device_id)},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": f"Device Type: {self._neostat.device_type}",
            "suggested_area": self._neostat.name,
            "sw_version": self.data.stat_version
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
        return f"{self._neostat.name} Heatmiser {HEATMISER_PRODUCT_LIST[self._neostat.device_type]}"

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def state(self):
        """Return the entity state."""
        # TODO: Revisit this, not sure state is reflected correctly.
        return 'on' if self.data.timer_on else 'off'

    async def async_turn_on(self, **kwargs):
        """ Turn the switch on. """
        _LOGGER.info(f"{self.name} : Executing turn_on() with: {kwargs}")

        # Clear all hold timers, we're going into manual mode.
        await self._hub.set_timer_hold(True, 0, [self._neostat])
        await self._hub.set_timer_hold(False, 0, [self._neostat])

        # We need to disable the TimeClock as we're going manual
        #
        # {“MANUAL_ON”:<devices>} Disables the timeclock built into the neoplug

        await self._hub.set_manual(False, [self._neostat])
        await self._hub.set_timer(True, [self._neostat])

    async def async_turn_off(self, **kwargs):
        """ Turn the switch off. """
        _LOGGER.info(f"{self.name} : Executing turn_off() with: {kwargs}")

        # Clear all hold timers, we're going into manual mode.
        await self._hub.set_timer_hold(True, 0, [self._neostat])
        await self._hub.set_timer_hold(False, 0, [self._neostat])
        await self._hub.set_timer(False, [self._neostat])
        # TODO: Should we Reinstates the timeclock built into the Neoplug based on configuration switch.
        # await self._hub.set_manual(True, [self._neostat])

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neostat.device_id}_heatmiser_neo_plug"


class HeatmiserNeoPlugTimerSwitch(CoordinatorEntity, SwitchEntity):
    """Represents a switch to control a Heatmiser Neo Plug's Time Clock function."""

    """
    Handles:
    {“MANUAL_ON”:<devices>} Disables the timeclock built into the neoplug
    {“MANUAL_OFF”:<devices>} Reinstates the timeclock built into the Neoplug
    """

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

    @property
    def data(self):
        """Helper to get the data for the current Heatmiser Neo device."""
        (devices, _) = self._coordinator.data
        neo_devices = {device.name: device for device in devices["neo_devices"]}
        return neo_devices[self._neostat.name]

    @property
    def available(self):
        """Return true if the entity is available."""
        if self.data.offline:
            return False
        else:
            return True

    @property
    def device_class(self):
        return SwitchDeviceClass.SWITCH

    @property
    def device_info(self):
        return {
            "identifiers": {("Heatmiser Neo Device", self._neostat.device_id)},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": f"Device Type: {self._neostat.device_type}",
            "suggested_area": self._neostat.name,
            "sw_version": self.data.stat_version
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
    def icon(self):
        if self.data.manual_off:
            return "mdi:timer-off"

        elif not self.data.manual_off:
            return "mdi:timer"

        else:
            return "mdi:timer-alert-outline"

    @property
    def is_on(self):
        """Return true if the binary sensor is on. i.e. Contacts are open"""
        return bool(self.data.manual_off)

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._neostat.name} Heatmiser Neo Timer Enabled"

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    async def async_turn_on(self, **kwargs):
        """ Turn the switch on. """
        _LOGGER.info(f"{self.name} : Executing turn_on() with: {kwargs}")
        response = await self._hub.set_manual(False, [self._neostat])

    async def async_turn_off(self, **kwargs):
        """ Turn the switch off. """
        _LOGGER.info(f"{self.name} : Executing turn_off() with: {kwargs}")
        response = await self._hub.set_manual(True, [self._neostat])

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neostat.device_id}_heatmiser_neo_plug_timer_switch"


class HeatmiserTemperatureHoldSwitch(CoordinatorEntity, SwitchEntity):
    """Represents a Heatmiser Neo Plug"""

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
        self._state = neostat.timer_on

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        neo_devices = {device.name: device for device in devices["neo_devices"]}
        return neo_devices[self._neostat.name]

    @property
    def available(self):
        """Return true if the entity is available."""
        if self.data.offline:
            return False
        else:
            return True

    @property
    def device_class(self):
        return SwitchDeviceClass.SWITCH

    @property
    def device_info(self):
        return {
            "identifiers": {("Heatmiser Neo Device", self._neostat.device_id)},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": f"Device Type: {self._neostat.device_type}",
            "suggested_area": self._neostat.name,
            "sw_version": self.data.stat_version
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
        return f"{self._neostat.name} Heatmiser {HEATMISER_PRODUCT_LIST[self._neostat.device_type]} Temperature Hold"

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def state(self):
        """Return the entity state."""
        return 'on' if self.data.hold_on else 'off'

    async def async_turn_on(self, **kwargs):
        """ Turn the switch on. """
        _LOGGER.info(
            f"Hold Hours: {self._neostat.hold_hours} Hold Mins: {self._neostat.hold_mins} Hold Temp: {self._neostat.hold_temp}")
        _LOGGER.info(
            f"Device ID: {self._neostat.device_id} - {self._neostat.name} : Executing turn_on() with: {kwargs}")
        await self._hub.set_hold(self._neostat.hold_temp, int(self._neostat.hold_hours), int(self._neostat.hold_mins), [self._neostat])

    async def async_turn_off(self, **kwargs):
        """ Turn the switch off. """
        _LOGGER.info(
            f"Device ID: {self._neostat.device_id} - {self._neostat.name} : Executing turn_off() with: {kwargs}")
        await self._hub.set_hold(self._neostat.hold_temp, 0, 0, [self._neostat])

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neostat.device_id}_heatmiser_neo_device_temperature_hold_switch"


class HeatmiserTimerHoldSwitch(CoordinatorEntity, SwitchEntity):
    """Represents a Heatmiser Neo Plug"""

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
        self._state = neostat.timer_on

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        neo_devices = {device.name: device for device in devices["neo_devices"]}
        return neo_devices[self._neostat.name]

    @property
    def available(self):
        """Return true if the entity is available."""
        if self.data.offline:
            return False
        else:
            return True

    @property
    def device_class(self):
        return SwitchDeviceClass.SWITCH

    @property
    def device_info(self):
        return {
            "identifiers": {("Heatmiser Neo Device", self._neostat.device_id)},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": f"Device Type: {self._neostat.device_type}",
            "suggested_area": self._neostat.name,
            "sw_version": self.data.stat_version
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
        return f"{self._neostat.name} Heatmiser {HEATMISER_PRODUCT_LIST[self._neostat.device_type]} Timer Hold"

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def state(self):
        """Return the entity state."""
        return 'on' if self.data.hold_on else 'off'

    async def async_turn_on(self, **kwargs):
        """ Turn on Timer Hold mode. """
        total_hold_minutes = int((self._neostat.hold_hours * 60) + self._neostat.hold_mins)
        _LOGGER.info(f"Device ID: {self._neostat.device_id} - {self._neostat.name}: Executing turn_on() with:"
                     f"Hold State: {self._neostat.hold_state}, Total Hold Minutes: {total_hold_minutes}")
        await self._hub.set_timer_hold(self._neostat.hold_state, total_hold_minutes, [self._neostat])

    async def async_turn_off(self, **kwargs):
        """ Turn the switch off. """
        _LOGGER.info(f"Device ID: {self._neostat.device_id} - {self._neostat.name}: Executing turn_off() with:"
                     f" {kwargs}")
        await self._hub.set_timer_hold(True, 0, [self._neostat])
        await self._hub.set_timer_hold(False, 0, [self._neostat])

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neostat.device_id}_heatmiser_neo_device_timer_hold_switch"


class HeatmiserTimerHoldStateSwitch(CoordinatorEntity, SwitchEntity):
    """Represents a Heatmiser Neo Plug"""

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
        self._state = neostat.hold_state

    @property
    def data(self):
        """Helper to get the data for the current thermostat."""
        (devices, _) = self._coordinator.data
        neo_devices = {device.name: device for device in devices["neo_devices"]}
        return neo_devices[self._neostat.name]

    @property
    def available(self):
        """Return true if the entity is available."""
        if self.data.offline:
            return False
        else:
            return True

    @property
    def device_class(self):
        return SwitchDeviceClass.SWITCH

    @property
    def device_info(self):
        return {
            "identifiers": {("Heatmiser Neo Device", self._neostat.device_id)},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": f"Device Type: {self._neostat.device_type}",
            "suggested_area": self._neostat.name,
            "sw_version": self.data.stat_version
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
        return f"{self._neostat.name} Heatmiser {HEATMISER_PRODUCT_LIST[self._neostat.device_type]} Hold State"

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def state(self):
        """Return the entity state."""
        if self._neostat.hold_state:
            return 'on'
        else:
            return 'off'

    async def async_turn_on(self, **kwargs):
        """ Turn on Timer Hold mode. """
        self._neostat.hold_state = True

    async def async_turn_off(self, **kwargs):
        """ Turn the switch off. """
        self._neostat.hold_state = False

    @property
    def unique_id(self):
        """Return a unique ID"""
        return f"{self._neostat.device_id}_heatmiser_neo_device_hold_state_switch"
