"""Discovery of Heatmiser Neo Hubs."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
import logging

from homeassistant import config_entries
from homeassistant.components import network
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, discovery_flow

from .api.discovery import (
    AIOHeatmiserAutoConnect,
    AIOHeatmiserDiscovery,
    NeoHubConnectDetails,
    NeoHubDetails,
)
from .const import DISCOVER_AUTO_CONNECT_TIMEOUT, DISCOVER_SCAN_TIMEOUT, DOMAIN

_LOGGER = logging.getLogger(__name__)

_discovery_lock = asyncio.Lock()


@callback
def async_update_entry_from_discovery(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    device: NeoHubDetails,
) -> bool:
    """Update a config entry from a discovery."""
    if not entry.unique_id or entry.unique_id.count(":") != 5:
        _LOGGER.debug("Adding unique id from discovery: %s", device)
        return hass.config_entries.async_update_entry(
            entry, unique_id=dr.format_mac(device.mac_address)
        )
    _LOGGER.debug("Unique id is already present from discovery: %s", device)
    return False


async def async_discover_devices(
    hass: HomeAssistant, timeout: int, address: str | None = None
) -> list[NeoHubDetails]:
    """Discover NeoHub devices."""

    async with _discovery_lock:  # Use the module-level lock
        targetted_address = False
        if address:
            targets = [address]
            targetted_address = True
        else:
            targets = [
                str(broadcast_address)
                for broadcast_address in await network.async_get_ipv4_broadcast_addresses(
                    hass
                )
            ]

        scanner = AIOHeatmiserDiscovery()
        combined_discoveries: dict[str, NeoHubDetails] = {}
        for idx, discovered in enumerate(
            await asyncio.gather(
                *[
                    scanner.async_scan(
                        timeout=timeout,
                        address=target_address,
                        targetted_address=targetted_address,
                    )
                    for target_address in targets
                ],
                return_exceptions=True,
            )
        ):
            if isinstance(discovered, Exception):
                _LOGGER.debug(
                    "Scanning %s failed with error: %s", targets[idx], discovered
                )
                continue
            if isinstance(discovered, BaseException):
                raise discovered from None
            for device in discovered:
                assert isinstance(device, NeoHubDetails)
                combined_discoveries[device.ip_address] = device

        return list(combined_discoveries.values())


async def async_discover_device(hass: HomeAssistant, host: str) -> NeoHubDetails | None:
    """Direct discovery at a single ip instead of broadcast."""
    # If we are missing the unique_id we should be able to fetch it
    # from the device by doing a directed discovery at the host only
    for device in await async_discover_devices(hass, DISCOVER_SCAN_TIMEOUT, host):
        return device
    return None


@callback
def async_trigger_discovery(
    hass: HomeAssistant,
    discovered_devices: list[NeoHubDetails],
) -> None:
    """Trigger config flows for discovered devices."""
    for device in discovered_devices:
        discovery_flow.async_create_flow(
            hass,
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=asdict(device),
        )


async def async_discover_device_connection_details(
    hass: HomeAssistant,
) -> NeoHubConnectDetails | None:
    """Listen for connect response."""
    async with _discovery_lock:  # Use the module-level lock
        scanner = AIOHeatmiserAutoConnect()
        discovered = await scanner.async_scan(timeout=DISCOVER_AUTO_CONNECT_TIMEOUT)
        if isinstance(discovered, BaseException):
            raise discovered from None
        if discovered:
            assert isinstance(discovered, NeoHubConnectDetails)
            return discovered
    return None
