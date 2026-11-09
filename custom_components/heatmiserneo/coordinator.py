# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
"""Coordinator object for the HeatmiserNeo integration."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from neohubapi.neohub import (
    ATTR_DEVICES,
    ATTR_LIVE,
    ATTR_PROFILES,
    ATTR_PROFILES_0,
    ATTR_SYSTEM,
    ATTR_TIMER_PROFILES,
    ATTR_TIMER_PROFILES_0,
    NeoHub,
    NeoStat,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

type HeatmiserNeoConfigEntry = ConfigEntry[HeatmiserNeoData]

type HeatmiserNeoCoordinatorData = tuple[dict[str, NeoStat], dict[str, Any]]

KNOWN_PENDING_MASKS = (0x80, 0xC0)


class HeatmiserNeoCoordinator(DataUpdateCoordinator[HeatmiserNeoCoordinatorData]):
    """Coordinator Class for Heatmiser Neo Hub."""

    # _device_serial_numbers: dict[int, dict[str, str]]

    def __init__(
        self, hass: HomeAssistant, entry: HeatmiserNeoConfigEntry, hub: NeoHub
    ) -> None:
        """Initialize the HeatmiserNeo Update Coordinator."""
        self.hub = hub
        super().__init__(
            hass,
            _LOGGER,
            name=f"Heatmiser NeoHub : {hub._host}",  # noqa: SLF001
            update_interval=timedelta(seconds=30),
            always_update=True,
            config_entry=entry,
        )
        self.previous_device_sns: set[str] = set()
        self._write_states: dict[str, WriteCountState] = {}
        assert self.config_entry

    async def _async_update_data(self) -> HeatmiserNeoCoordinatorData:
        """Fetch data from the Hub all at once and make it available for all devices."""
        _LOGGER.info("Executing update_data()")
        async with asyncio.timeout(30):
            all_live_data = await self.hub.get_all_live_data()

            if not all_live_data[ATTR_SYSTEM]:
                ## System data is very important. If it is not returned by the API
                ## Try getting it directly
                all_live_data[ATTR_SYSTEM] = await self.hub.get_system()

            _LOGGER.debug("live_data: %s", all_live_data)

            devices = {device.name: device for device in all_live_data[ATTR_DEVICES]}
            current_device_sns = {dev.serial_number for dev in devices.values()}
            if stale_devices := self.previous_device_sns - current_device_sns:
                assert self.config_entry
                device_registry = dr.async_get(self.hass)
                for serial_number in stale_devices:
                    identifiers = {
                        (
                            DOMAIN,
                            f"{self.config_entry.unique_id}_{serial_number}",
                        )
                    }
                    device = device_registry.async_get_device(identifiers=identifiers)
                    if device:
                        device_registry.async_update_device(
                            device_id=device.id,
                            remove_config_entry_id=self.config_entry.entry_id,
                        )
            self.previous_device_sns = current_device_sns

            for device in devices.values():
                self._write_pending(device)

            return devices, all_live_data

    def update_in_memory_state(
        self, action: Callable[[NeoStat], None], filter: Callable[[NeoStat], bool]
    ) -> None:
        """Call action on devices matching filter."""
        devices, _ = self.data
        for device in devices.values():
            if filter(device):
                action(device)

    @property
    def live_data(self):
        """Helper to get the data for the current device."""
        (_, all_data) = self.data
        return all_data[ATTR_LIVE]

    @property
    def system_data(self):
        """Helper to get the data for the current device."""
        (_, all_data) = self.data
        return all_data[ATTR_SYSTEM]

    @property
    def profiles(self):
        """Helper to get the data for the current device."""
        (_, all_data) = self.data
        return all_data.get(ATTR_PROFILES, {})

    @property
    def profiles_0(self):
        """Helper to get the data for the current device."""
        (_, all_data) = self.data
        return all_data.get(ATTR_PROFILES_0, {})

    @property
    def timer_profiles(self):
        """Helper to get the data for the current device."""
        (_, all_data) = self.data
        return all_data.get(ATTR_TIMER_PROFILES, {})

    @property
    def timer_profiles_0(self):
        """Helper to get the data for the current device."""
        (_, all_data) = self.data
        return all_data.get(ATTR_TIMER_PROFILES_0, {})

    def has_write_pending(self, device: NeoStat) -> bool:
        """Return True if there is a pending write for this device."""
        serial = device.serial_number
        state = self._write_states.get(serial)
        return state.pending if state else False

    def _write_pending(self, device: NeoStat) -> bool:
        """Return True if HA state updates for this device should be suppressed."""
        serial = device.serial_number
        current = device.write_count

        state = self._write_states.get(serial)
        if state is None:
            self._write_states[serial] = WriteCountState(
                last_seen=current,
                confirmed=current,
            )
            return False

        if not state.pending:
            diff = current ^ state.last_seen
            if diff in KNOWN_PENDING_MASKS:
                state.pending = True
                state.mask = diff
                state.last_seen = current
                return True

            # normal change or unchanged
            state.confirmed = current
            state.last_seen = current
            return False

        # currently pending
        expected_pending = state.confirmed ^ (state.mask or 0)
        if current == expected_pending:
            state.last_seen = current
            return True  # still pending

        # resolved (or unexpected; just accept the new value)
        state.pending = False
        state.confirmed = current
        state.last_seen = current
        return False


@dataclass
class HeatmiserNeoData:
    """Class to store Heatmiser Neo runtime data."""

    hub: NeoHub
    coordinator: HeatmiserNeoCoordinator


@dataclass
class WriteCountState:
    """Class to store the write count state."""

    last_seen: int = 0
    confirmed: int = 0
    pending: bool = False
    mask: int | None = None
