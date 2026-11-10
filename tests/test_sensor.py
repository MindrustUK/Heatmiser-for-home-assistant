# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
"""Tests for the Heatmiser Neo sensor platform."""

from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from unittest.mock import patch

from custom_components.heatmiserneo.coordinator import HeatmiserNeoData
import pytest
from pytest_homeassistant.common import MockConfigEntry

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor_entities(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_hub: SimpleNamespace,
    snapshot_platform: Callable[[str, Platform], Awaitable[None]],
) -> None:
    """Test sensor entities for the Kitchen and Hot Water zones."""
    with (
        patch("custom_components.heatmiserneo.NeoHub", return_value=mock_hub),
        patch("custom_components.heatmiserneo.PLATFORMS", [Platform.SENSOR]),
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert isinstance(config_entry.runtime_data, HeatmiserNeoData)
    await snapshot_platform(config_entry.entry_id, Platform.SENSOR)
