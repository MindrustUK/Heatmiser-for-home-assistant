# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""
homeassistant.components.button.heatmiserneo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from datetime import time
import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from neohubapi.neohub import NeoHub, NeoStat
from .const import DOMAIN, HUB, COORDINATOR, HEATMISER_PRODUCT_LIST


async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id][HUB]
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]

    if coordinator.data is None:
        _LOGGER.error("Coordinator data is None. Cannot set up button entities.")
        return

    devices_data, _ = coordinator.data

    neo_devices = {device.name: device for device in devices_data["neo_devices"]}
    _LOGGER.info(f"neo_devices: {neo_devices}")
    list_of_neo_devices = []
    for neo_device in neo_devices.values():
        list_of_neo_devices.append(HeatmiserNeoIdentifyButton(neo_device, coordinator, hub))

    _LOGGER.info(f"Adding Neo Device Identify Buttons: {list_of_neo_devices}")
    async_add_entities(list_of_neo_devices, True)


_LOGGER = logging.getLogger(__name__)


class HeatmiserNeoIdentifyButton(CoordinatorEntity, ButtonEntity):

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
        return ButtonDeviceClass.IDENTIFY

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._coordinator.serial_number}_{self._neostat.serial_number}")},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": f"{HEATMISER_PRODUCT_LIST[self.data.device_type]}",
            "suggested_area": self._neostat.name,
            "serial_number": self._neostat.serial_number,
            "sw_version": self.data.stat_version,
            "via_device": (DOMAIN, self._coordinator.serial_number),
        }

    @property
    def entity_category(self):
        """Return the Entity Category."""
        return EntityCategory.DIAGNOSTIC

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
        return f"{self._neostat.name} Heatmiser Neo Identify Device"

    @property
    def should_poll(self):
        """Don't poll - we fetch the data from the hub all at once"""
        return False

    @property
    def unique_id(self):
        """Return a unique ID"""
        # Use both the Hub and Device serial numbers as you can have orphaned devices still present in hub configuration.
        return f"{self._neostat.name}_{self._coordinator.serial_number}_{self._neostat.serial_number}_heatmiser_neo_identify_button"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._neostat.identify()
