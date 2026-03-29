"""Define fixtures for AirNow tests."""

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
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Automatically enable loading of custom integrations in all tests."""
    return


@pytest.fixture(name="config_entry")
def config_entry_fixture(
    hass: HomeAssistant,  # , config: dict[str, Any], options: dict[str, Any]
) -> MockConfigEntry:
    """Mock a config entry for the integration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "test-hub", "port": 1234},
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
    # entry.runtime_data = HeatmiserNeoData(AsyncMock(), AsyncMock())
    entry.add_to_hass(hass)
    return entry
