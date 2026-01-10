# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
"""Define fixtures for Heatmiser Neo tests."""

from collections.abc import Callable, Coroutine
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from custom_components.heatmiserneo.const import (
    CONF_DEFAULTS,
    CONF_HVAC_MODES,
    CONF_STAT_HOLD_DURATION,
    CONF_STAT_HOLD_TEMP,
    CONF_STAT_MAX_TEMPERATURE,
    CONF_STAT_MIN_TEMPERATURE,
    CONF_THERMOSTAT_OPTIONS,
    CONF_TIMER_HOLD_DURATION,
    CONF_TIMER_OPTIONS,
    DOMAIN,
    AvailableMode,
)
from neohubapi.neohub import (
    ATTR_DEVICES,
    ATTR_LIVE,
    ATTR_PROFILES,
    ATTR_PROFILES_0,
    ATTR_SYSTEM,
    ATTR_TIMER_PROFILES,
    ATTR_TIMER_PROFILES_0,
    NeoStat,
    ScheduleFormat,
)
import pytest
from pytest_homeassistant.common import MockConfigEntry, load_json_object_fixture
from syrupy.assertion import SnapshotAssertion

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


@pytest.fixture(name="diagnostics")
def diagnostics_fixture() -> dict[str, Any]:
    """Load the redacted diagnostics sample."""
    return load_json_object_fixture(
        str(Path(__file__).parent / "samples" / "diagnostics.json"), DOMAIN
    )


@pytest.fixture(name="mock_hub")
def mock_hub_fixture(diagnostics: dict[str, Any]) -> SimpleNamespace:
    """Mock the hub with the Kitchen and Hot Water devices from diagnostics."""
    data = diagnostics["data"]
    hub = SimpleNamespace(
        _host="test-hub",
        disconnect=AsyncMock(),
        target_temperature_step=AsyncMock(return_value=0.5),
    )
    devices = []
    for device_data in data["devices_data"]:
        raw_data = device_data["raw_data"].copy()
        raw_data["PIN_NUMBER"] = 0
        devices.append(NeoStat(hub, SimpleNamespace(**raw_data)))

    system_data = data["system_data"].copy()
    system_data["FORMAT"] = ScheduleFormat[system_data["FORMAT"]]
    system_data["ALT_TIMER_FORMAT"] = ScheduleFormat[system_data["ALT_TIMER_FORMAT"]]

    hub.get_all_live_data = AsyncMock(
        return_value={
            ATTR_DEVICES: devices,
            ATTR_LIVE: SimpleNamespace(**data["live_data"]),
            ATTR_SYSTEM: SimpleNamespace(**system_data),
            ATTR_PROFILES: _profile_data(data["profiles"]),
            ATTR_PROFILES_0: _profile_data(data["profiles_0"]),
            ATTR_TIMER_PROFILES: _profile_data(data["timer_profiles"]),
            ATTR_TIMER_PROFILES_0: _profile_data(data["timer_profiles_0"]),
        }
    )
    return hub


def _profile_data(data: dict[str, Any]) -> dict[int, SimpleNamespace]:
    """Convert serialized profile data to the objects returned by neohubapi."""
    return {int(key): _to_namespace(value) for key, value in data.items()}


def _to_namespace(value: Any) -> Any:
    """Convert nested diagnostic dictionaries to attribute-accessible objects."""
    if isinstance(value, dict):
        return SimpleNamespace(
            **{key: _to_namespace(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return [_to_namespace(item) for item in value]
    return value


@pytest.fixture
def snapshot_platform(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> Callable[[str, Platform], Coroutine[Any, Any, None]]:
    """Snapshot a platform, including entities that are disabled by default."""

    async def async_snapshot_platform(config_entry_id: str, platform: Platform) -> None:
        entity_entries = [
            entity_entry
            for entity_entry in er.async_entries_for_config_entry(
                entity_registry, config_entry_id
            )
            if entity_entry.domain == platform.value
        ]
        assert entity_entries
        for entity_entry in entity_entries:
            assert entity_entry == snapshot(name=f"{entity_entry.entity_id}-entry")
            state = hass.states.get(entity_entry.entity_id)
            if entity_entry.disabled_by is not None:
                assert state is None
                continue
            assert state is not None
            assert state == snapshot(name=f"{entity_entry.entity_id}-state")

    return async_snapshot_platform


@pytest.fixture(name="config_entry")
def config_entry_fixture(
    hass: HomeAssistant,
) -> MockConfigEntry:
    """Mock a config entry for the integration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "test-hub", "port": 1234},
        unique_id="aa:bb:cc:dd:ee:ff",
        options={
            CONF_DEFAULTS: {
                CONF_THERMOSTAT_OPTIONS: {
                    CONF_STAT_HOLD_TEMP: 1,
                    CONF_STAT_HOLD_DURATION: 15,
                    CONF_STAT_MIN_TEMPERATURE: 5.0,
                    CONF_STAT_MAX_TEMPERATURE: 20.0,
                },
                CONF_TIMER_OPTIONS: {CONF_TIMER_HOLD_DURATION: 17},
            },
            CONF_HVAC_MODES: {"TEST_HC": {AvailableMode.HEAT}},
        },
    )
    entry.add_to_hass(hass)
    return entry
