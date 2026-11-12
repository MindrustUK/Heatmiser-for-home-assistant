# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
"""Tests for the Heatmiser Neo coordinator."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

from custom_components.heatmiserneo.coordinator import HeatmiserNeoCoordinator
from neohubapi.neohub import ATTR_DEVICES, ATTR_SYSTEM
from pytest_homeassistant.common import MockConfigEntry

from homeassistant.core import HomeAssistant


async def test_coordinator_fetches_system_data_when_bulk_response_has_none(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Test system data is fetched separately when missing from the bulk response."""
    system_data = SimpleNamespace(CORF="C", GLOBAL_SYSTEM_TYPE="HEAT_ONLY")
    hub = SimpleNamespace(
        _host="test-hub",
        get_all_live_data=AsyncMock(return_value={ATTR_DEVICES: [], ATTR_SYSTEM: None}),
        get_system=AsyncMock(return_value=system_data),
    )
    coordinator = HeatmiserNeoCoordinator(hass, config_entry, hub)

    await coordinator.async_refresh()

    hub.get_system.assert_awaited_once()
    assert coordinator.system_data is system_data
