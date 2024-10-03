# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
import asyncio
from .const import DOMAIN, HUB, COORDINATOR, HEATMISER_HUB_PRODUCT_LIST
from datetime import timedelta
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import (CoordinatorEntity, DataUpdateCoordinator)
from neohubapi.neohub import NeoHub
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Set up Heatmiser Neo components."""
    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(hass, entry):
    """Set up Heatmiser Neo from a config entry."""

    # Set the Hub up to use and save
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    # Make this configurable or retrieve from an API later.
    hub_serial_number = f"NEOHUB-SN:000000-{host}"
    hub = NeoHub(host, port)

    # TODO: Split this out to it's own HUB / Bridge thing.
    _LOGGER.debug(f"Attempting to setup Heatmiser Neo Hub Device: {host}:{port}")
    init_system_data = await hub.get_system()
    _LOGGER.debug(f"system_data: {init_system_data}")

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, hub_serial_number)},
        manufacturer="Heatmiser",
        model=f"{HEATMISER_HUB_PRODUCT_LIST[init_system_data.HUB_TYPE]}",
        name=f"NeoHub - {host}",
        serial_number=hub_serial_number,
        sw_version=init_system_data.HUB_VERSION
    )

    # TODO: NTP Fixes as per below.
    """"
    TODO: Make this configurable, and move it from here
    workaround to re-enable NTP after a power outage (or any other reason) 
    where WAN connectivity will not have been restored by the time the NeoHub has fully started.
    """
    if getattr(init_system_data, "NTP_ON") != "Running":

        """ Enable NTP """
        _LOGGER.warning(f"NTP disabled. Enabling")

        set_ntp_enabled_task = asyncio.create_task(hub.set_ntp(True))
        response = await set_ntp_enabled_task
        if response:
            _LOGGER.info(f"Enabled NTP (response: {response})")
    else:
        _LOGGER.debug(f"NTP enabled")


    async def async_update_data():
        """Fetch data from the Hub all at once and make it available for all devices."""
        _LOGGER.info("Executing update_data()")
        async with asyncio.timeout(30):
            system_data = await hub.get_system()
            devices_data = await hub.get_devices_data()
            device_serial_numbers = await hub.devices_sn()

            _LOGGER.debug(f"system_data: {system_data}")
            _LOGGER.debug(f"devices_data: {devices_data}")
            _LOGGER.debug(f"device_serial_numbers: {device_serial_numbers}")

            ## Adding Serial numbers to device data.
            # Convert device_serial_numbers (SimpleNamespace) to a dictionary
            device_serial_numbers_dict = vars(device_serial_numbers)

            # Loop through devices and append serial numbers to _simple_attrs
            for device in devices_data['neo_devices']:
                device_id = device._data_.DEVICE_ID  # Get the device ID from the _data_ namespace

                # Find the corresponding serial number from the dictionary using the DEVICE_ID
                matching_serials = [
                    serial[1] for serial in device_serial_numbers_dict.values() if serial[0] == device_id
                ]

                # If any matching serials are found, assign the first one, else set to "UNKNOWN"
                serial_number = matching_serials[0] if matching_serials else "UNKNOWN"

                # Create a new tuple that includes the serial number in _simple_attrs
                if 'serial_number' not in device._simple_attrs:
                    device._simple_attrs = tuple(list(device._simple_attrs) + ['serial_number'])

                # Dynamically set the serial_number as an attribute of the _data_ object
                setattr(device, 'serial_number', serial_number)

            return devices_data, system_data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"Heatmiser NeoHub : {host}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
        always_update=True
    )

    coordinator.serial_number = hub_serial_number

    # Store hub and coordinator per entry_id
    hass.data[DOMAIN][entry.entry_id] = {
        HUB: hub,
        COORDINATOR: coordinator,
    }

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, ["button", "climate", "number", "sensor", "switch"])

    return True


async def options_update_listener(hass: HomeAssistant, config_entry: config_entries.ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
