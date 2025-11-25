# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
"""The Heatmiser Neo integration."""

import asyncio
import logging
from typing import Any

from neohubapi.neohub import NeoHub, NeoStat

from homeassistant.const import CONF_API_TOKEN, CONF_HOST, CONF_PORT, Platform
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.helpers.issue_registry as ir
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType

from .const import (
    DISCOVER_SCAN_TIMEOUT,
    DISCOVERY_INTERVAL,
    DOMAIN,
    HEATMISER_TYPE_IDS_REPEATER,
    ISSUE_ID_CLEANUP_OLD_DEVICES,
)
from .coordinator import (
    HeatmiserNeoConfigEntry,
    HeatmiserNeoCoordinator,
    HeatmiserNeoData,
)
from .discovery import (
    async_discover_device,
    async_discover_devices,
    async_trigger_discovery,
    async_update_entry_from_discovery,
)
from .services import async_setup_services
from .utils import unique_id_is_mac

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.LOCK,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

_OLD_SERIAL_NUMBER_PREFIX = "NEOHUB-SN:000000"


async def async_setup(hass: HomeAssistant, hass_config: ConfigType) -> bool:
    """Set up the Heatmiser Neo integration."""

    async def _async_discovery(*_: Any) -> None:
        async_trigger_discovery(
            hass, await async_discover_devices(hass, DISCOVER_SCAN_TIMEOUT)
        )

    async_track_time_interval(
        hass, _async_discovery, DISCOVERY_INTERVAL, cancel_on_shutdown=True
    )

    async_setup_services(hass)

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatmiserNeoConfigEntry,
) -> bool:
    """Set up Heatmiser Neo from a config entry."""
    # Set the Hub up to use and save
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    token = entry.data.get(CONF_API_TOKEN)

    if not unique_id_is_mac(entry.unique_id):

        async def attempt_discovery(hass: HomeAssistant):
            _LOGGER.debug(
                "Unique id for %s is missing during setup or it is not a MAC address, trying to fill from discovery",
                host,
            )
            if device := await async_discover_device(hass, host):
                async_update_entry_from_discovery(hass, entry, device)

        if hass.state is CoreState.running:
            await attempt_discovery(hass)
        else:
            entry.async_on_unload(async_at_started(hass, attempt_discovery))

    await _async_migrate_unique_ids(hass, entry)

    if token:
        hub = NeoHub(host, port, token=token)
    else:
        hub = NeoHub(host, port)

    coordinator = HeatmiserNeoCoordinator(hass, entry, hub)

    entry.runtime_data = HeatmiserNeoData(hub, coordinator)

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(
    hass: HomeAssistant, entry: HeatmiserNeoConfigEntry
) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: HeatmiserNeoConfigEntry
) -> bool:
    """Unload a config entry."""
    hub = entry.runtime_data.hub
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    await hub.disconnect()

    return unload_ok


async def options_update_listener(
    hass: HomeAssistant, config_entry: HeatmiserNeoConfigEntry
):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def _async_migrate_unique_ids(
    hass: HomeAssistant, entry: HeatmiserNeoConfigEntry
) -> None:
    """Migrate pre-config flow unique ids."""

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    registry_entries = er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    )
    registry_devices = {
        dev.id: dev
        for dev in dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    }

    # Migrate
    hub_updated = False

    num_hub_devices = len([d for d in registry_devices.values() if not d.via_device_id])
    if num_hub_devices > 1:
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_ID_CLEANUP_OLD_DEVICES.format(entry_id=entry.entry_id),
            is_fixable=True,
            severity=ir.IssueSeverity.ERROR,
            translation_key="cleanup_old_devices",
            data={"entry_id": entry.entry_id},
        )
        raise HomeAssistantError(
            f"Heatmiser Hub at {entry.data[CONF_HOST]}:{entry.data[CONF_PORT]} can't be configured because there are invalid devices"
        )

    for reg_device in registry_devices.values():
        if not reg_device.via_device_id:
            identifier_key = None
            if _has_old_identifier(reg_device) or (
                unique_id_is_mac(entry.unique_id)
                and not _has_mac_identifier(reg_device)
            ):
                if unique_id_is_mac(entry.unique_id):
                    identifier_key = dr.CONNECTION_NETWORK_MAC
                else:
                    identifier_key = DOMAIN
            if identifier_key:
                assert entry.unique_id
                new_identifiers = {(identifier_key, entry.unique_id)}
                _LOGGER.debug(
                    "Existing Hub device %s has identifiers %s and serial number %s. Updating to %s and removing serial number",
                    reg_device.id,
                    reg_device.identifiers,
                    reg_device.serial_number,
                    new_identifiers,
                )
                device_registry.async_update_device(
                    device_id=reg_device.id,
                    new_identifiers=new_identifiers,
                    serial_number=None,
                )
                hub_updated = True

    if hub_updated:
        for reg_device in registry_devices.values():
            if reg_device.via_device_id:
                identifier = next(iter(reg_device.identifiers))[1]
                parts = identifier.split("_", 1)
                if len(parts) > 1:
                    new_identifiers = {(DOMAIN, f"{entry.unique_id}_{parts[1]}")}
                    _LOGGER.debug(
                        "Existing device %s with via_device_id %s has identifiers %s. Updating to %s",
                        reg_device.id,
                        reg_device.via_device_id,
                        reg_device.identifiers,
                        new_identifiers,
                    )
                    device_registry.async_update_device(
                        device_id=reg_device.id,
                        new_identifiers=new_identifiers,
                    )

        for reg_entry in registry_entries:
            if not reg_entry.device_id:
                continue
            device = registry_devices.get(reg_entry.device_id)
            if not device:
                continue
            new_unique_id = None
            if not device.via_device_id:
                parts = reg_entry.unique_id.split("_", 1)
                new_unique_id = f"{entry.unique_id}_{parts[1]}"
            elif _OLD_SERIAL_NUMBER_PREFIX in reg_entry.unique_id:
                parts = reg_entry.unique_id.split("_", 3)
                new_unique_id = f"{entry.unique_id}_{parts[2]}_{parts[3]}"
            else:
                parts = reg_entry.unique_id.split("_", 2)
                new_unique_id = f"{entry.unique_id}_{parts[1]}_{parts[2]}"
            _LOGGER.debug(
                "Existing entity %s on device %s has unique id %s. Updating to %s",
                reg_entry.entity_id,
                reg_entry.device_id,
                reg_entry.unique_id,
                new_unique_id,
            )
            entity_registry.async_update_entity(
                entity_id=reg_entry.entity_id, new_unique_id=new_unique_id
            )


def _has_old_identifier(device: dr.DeviceEntry) -> bool:
    for ident in device.identifiers:
        if ident[0] == DOMAIN and _OLD_SERIAL_NUMBER_PREFIX in ident[1]:
            return True
    return False


def _has_mac_identifier(device: dr.DeviceEntry) -> bool:
    return any(ident[0] == dr.CONNECTION_NETWORK_MAC for ident in device.identifiers)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: HeatmiserNeoConfigEntry, device: dr.DeviceEntry
) -> bool:
    """Remove devices from hub."""
    if not device.via_device_id:
        # Hub device can't be removed. Remove whole config entry instead
        return False
    sn = device.serial_number
    devices, _ = config_entry.runtime_data.coordinator.data
    matching_devices = [dev for dev in devices.values() if dev.serial_number == sn]
    if matching_devices:
        for dev in matching_devices:
            if dev.device_type in HEATMISER_TYPE_IDS_REPEATER:
                await config_entry.runtime_data.coordinator.hub.remove_repeater(
                    dev.device_id
                )
            else:
                await dev.remove()
        return await _confirm_removal(
            config_entry.runtime_data.coordinator, matching_devices
        )
    return True


async def _confirm_removal(
    coordinator: HeatmiserNeoCoordinator, devices: list[NeoStat]
):
    timeout = 30
    poll_interval = 10
    start_time = asyncio.get_running_loop().time()
    removed_device_ids = {dev.device_id for dev in devices}
    while True:
        current_time = asyncio.get_running_loop().time()
        elapsed = current_time - start_time

        await coordinator.async_request_refresh()
        updated_devices, _ = coordinator.data
        updated_device_ids = {dev.device_id for dev in updated_devices.values()}

        if len(removed_device_ids - updated_device_ids) == len(removed_device_ids):
            return True

        if elapsed >= timeout:
            return False
        # Sleep briefly to update progress smoothly
        await asyncio.sleep(poll_interval)
