# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""
homeassistant.components.switch.heatmiserneo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from datetime import time
import logging

import voluptuous as vol
from homeassistant.const import EntityCategory
from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from neohubapi.neohub import NeoHub, NeoStat
from .const import COORDINATOR, DOMAIN, HUB, HEATMISER_PRODUCT_LIST
from .const import (
    ATTR_HOLD_DURATION,
    SERVICE_TIMER_HOLD_ON,
)

_LOGGER = logging.getLogger(__name__)

DEVICES_ENABLED_NEO_PLUG = True
HOLD_CONTROLS_ENABLED = True


async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id][HUB]
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]

    if coordinator.data is None:
        _LOGGER.error("Coordinator data is None. Cannot set up switche entities.")
        return

    devices_data, _ = coordinator.data

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

            # Neo plugs and Thermostats in Time Clock mode
            if (neo_device.device_type in [1, 2, 7, 12, 13]) and neo_device.time_clock_mode:
                # Switch to control standby mode
                list_of_neo_devices.append(NeoTimerEntity(neo_device, coordinator, hub))
                list_of_neo_devices.append(HeatmiserTimerDeviceStandbySwitch(neo_device, coordinator, hub))


    _LOGGER.info(f"Adding neoPlug switches: {list_of_neo_devices}")
    async_add_entities(list_of_neo_devices, True)

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_TIMER_HOLD_ON,
        {
            vol.Required(ATTR_HOLD_DURATION, default=1): cv.positive_time_period,
        },
        "async_turn_on",
    )


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
            "identifiers": {(DOMAIN, f"{self._coordinator.serial_number}_{self._neostat.serial_number}")},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": f"{HEATMISER_PRODUCT_LIST[self.data.device_type]}",
            "serial_number": self._neostat.serial_number,
            "suggested_area": self._neostat.name,
            "sw_version": self.data.stat_version,
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
        # Use both the Hub and Device serial numbers as you can have orphaned devices still present in hub configuration.
        return f"{self._neostat.name}_{self._coordinator.serial_number}_{self._neostat.serial_number}_heatmiser_neo_plug"


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
            "identifiers": {(DOMAIN, f"{self._coordinator.serial_number}_{self._neostat.serial_number}")},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": f"{HEATMISER_PRODUCT_LIST[self.data.device_type]}",
            "serial_number": self._neostat.serial_number,
            "suggested_area": self._neostat.name,
            "sw_version": self.data.stat_version,
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
        # Use both the Hub and Device serial numbers as you can have orphaned devices still present in hub configuration.
        return f"{self._neostat.name}_{self._coordinator.serial_number}_{self._neostat.serial_number}_heatmiser_neo_plug_timer_switch"


class HeatmiserTimerDeviceStandbySwitch(CoordinatorEntity, SwitchEntity):
    """Represents a Heatmiser Neostat Timer Device Standby Switch"""

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
        self._neostat.standby = neostat.standby

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
            "identifiers": {(DOMAIN, f"{self._coordinator.serial_number}_{self._neostat.serial_number}")},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": f"{HEATMISER_PRODUCT_LIST[self.data.device_type]}",
            "serial_number": self._neostat.serial_number,
            "suggested_area": self._neostat.name,
            "sw_version": self.data.stat_version,
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
    def icon(self):
        if self.data.offline:
            return "mdi:network-off-outline"

        elif self.data.standby:
            return "mdi:power-standby"

        elif not self.data.standby:
            return "mdi:power"

        else:
            return "mdi:image-broken-variant"

    @property
    def is_on(self):
        """Return is_on status."""
        return self.data.standby

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._neostat.name} Heatmiser {HEATMISER_PRODUCT_LIST[self._neostat.device_type]} Standby"

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def unique_id(self):
        """Return a unique ID"""
        # Use both the Hub and Device serial numbers as you can have orphaned devices still present in hub configuration.
        return f"{self._neostat.name}_{self._coordinator.serial_number}_{self._neostat.serial_number}_heatmiser_neo_timer_device_standby_switch"
        
    async def async_turn_on(self, **kwargs):
        """ Turn on Standby (Previously Frost) mode. """
        response = await self._neostat.set_frost(True)
        _LOGGER.info(f"{self.name} : Called set_frost with: True (response: {response})")
        self.data.standby = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """ Turn off Standby (Previously Frost) mode. """
        response = await self._neostat.set_frost(False)
        _LOGGER.info(f"{self.name} : Called set_frost with: False (response: {response})")
        self.data.standby = False
        self.async_write_ha_state()


class NeoTimerEntity(CoordinatorEntity, SwitchEntity):
    """Represents a Heatmiser neoStat thermostat acting in TimeClock mode."""

    def __init__(
        self, neostat: NeoStat, coordinator: DataUpdateCoordinator, hub: NeoHub
    ):
        super().__init__(coordinator)
        _LOGGER.debug(
            f"Creating {type(self).__name__} for {neostat.name} {neostat.device_id}"
        )

        self._neostat = neostat
        self._coordinator = coordinator
        self._hub = hub

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
        return True

    @property
    def device_class(self):
        return SwitchDeviceClass.SWITCH

    @property
    def device_info(self):
        return {
            "identifiers": {
                (
                    DOMAIN,
                    f"{self._coordinator.serial_number}_{self._neostat.serial_number}",
                )
            },
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": f"{HEATMISER_PRODUCT_LIST[self.data.device_type]}",
            "serial_number": self._neostat.serial_number,
            "suggested_area": self._neostat.name,
            "sw_version": self.data.stat_version,
            "via_device": (DOMAIN, self._coordinator.serial_number),
        }

    @property
    def extra_state_attributes(self):
        """Return the additional state attributes."""
        return {
            "device_id": self._neostat.device_id,
            "device_type": self._neostat.device_type,
            "offline": self.data.offline,
            "hold_on": self.data.hold_on,
            "hold_time": ":".join(str(self.data.hold_time).split(":")[:2]),
        }

    @property
    def name(self):
        """Returns the name."""
        return f"{self._neostat.name} Heatmiser {HEATMISER_PRODUCT_LIST[self._neostat.device_type]} Timer Override"

    @property
    def is_on(self):
        """Return is_on status."""
        return self.data.timer_on

    async def async_turn_on(self, **kwargs):
        """Turn on Timer"""
        hold_minutes = 30
        if ATTR_HOLD_DURATION in kwargs:
            hold_duration = kwargs.get(ATTR_HOLD_DURATION)
            hold_minutes = int(hold_duration.total_seconds() / 60)

        _LOGGER.info(
            f"Device Unique ID: {self.unique_id} - {self._neostat.name}: Executing turn_on() with:"
            f"Total Hold Minutes: {hold_minutes}"
        )
        result = await self._hub.set_timer_hold(True, hold_minutes, [self._neostat])

        hold_hours, remainder = divmod(hold_minutes, 60)
        self.data.timer_on = hold_minutes > 0
        self.data.hold_on = hold_minutes > 0
        self.data.hold_time = str(f"{hold_hours!s}:{str(remainder).ljust(2, '0')}")
        self.async_schedule_update_ha_state(False)
        return result

    async def async_turn_off(self, **kwargs):
        """Turn off Timer."""

        _LOGGER.info(
            f"Device Unique ID: {self.unique_id} - {self._neostat.name}: Executing turn_off()"
        )
        result = await self._hub.set_timer_hold(False, 0, [self._neostat])
        self.data.timer_on = False
        self.data.hold_on = False
        self.data.hold_time = "0:00"
        self.async_schedule_update_ha_state(False)
        return result

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def unique_id(self):
        """Return a unique ID"""
        # Use both the Hub and Device serial numbers as you can have orphaned devices still present in hub configuration.
        return f"{self._neostat.name}_{self._coordinator.serial_number}_{self._neostat.serial_number}_heatmiser_neotimer"
