"""Test the heatmiserneo config flow."""

from ipaddress import ip_address
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from custom_components.heatmiserneo.const import (
    CONF_CONN_METHOD_LEGACY,
    CONF_CONN_METHOD_WEBSOCKET,
    CONF_DEFAULTS,
    CONF_DISCOVERY_METHOD_MANUAL,
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
    GlobalSystemType,
)
from custom_components.heatmiserneo.coordinator import (
    HeatmiserNeoCoordinator,
    HeatmiserNeoData,
)
from neohubapi.neohub import (
    ATTR_DEVICES,
    ATTR_LIVE,
    ATTR_PROFILES,
    ATTR_PROFILES_0,
    ATTR_SYSTEM,
    ATTR_TIMER_PROFILES,
    ATTR_TIMER_PROFILES_0,
)
import pytest

from homeassistant.config_entries import (
    SOURCE_INTEGRATION_DISCOVERY,
    SOURCE_USER,
    SOURCE_ZEROCONF,
    ConfigEntry,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from homeassistant.helpers.typing import DiscoveryInfoType

ZEROCONF_DISCOVERY = ZeroconfServiceInfo(
    ip_address=ip_address("192.168.1.100"),
    ip_addresses=[ip_address("192.168.1.100")],
    hostname="neohub.local.",
    name="heatmiser neohub*",
    port=80,
    type="_hap._tcp.local.",
    properties={
        "id": "aa:bb:cc:dd:ee:ff",
    },
)

INTEGRATION_DISCOVERY: DiscoveryInfoType = {
    "mac_address": ZEROCONF_DISCOVERY.properties.get("id"),
    "ip_address": "192.168.1.100",
}


@pytest.mark.asyncio
async def test_form(
    hass: HomeAssistant,  # , config: dict[str, Any], options: dict[str, Any]
) -> None:
    """Test that the form is served with no input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "choose_discovery_method"


@pytest.mark.asyncio
async def test_create_manual_legacy(
    hass: HomeAssistant,  # , config: dict[str, Any], options: dict[str, Any]
) -> None:
    """Test that the form is served with no input."""
    menu_step = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert menu_step["type"] is FlowResultType.MENU
    assert menu_step["step_id"] == "choose_discovery_method"

    conn_menu_step = await hass.config_entries.flow.async_configure(
        menu_step["flow_id"],
        {"next_step_id": CONF_DISCOVERY_METHOD_MANUAL},
    )

    assert conn_menu_step["type"] is FlowResultType.MENU
    assert conn_menu_step["step_id"] == "choose_conn_method"

    legacy_conn_form = await hass.config_entries.flow.async_configure(
        conn_menu_step["flow_id"],
        {"next_step_id": CONF_CONN_METHOD_LEGACY},
    )

    assert legacy_conn_form["type"] is FlowResultType.FORM
    assert legacy_conn_form["step_id"] == CONF_CONN_METHOD_LEGACY

    # Mock the NeoHub to simulate successful connection
    with (
        patch("custom_components.heatmiserneo.config_flow.NeoHub") as mock_neohub_class,
        patch("custom_components.heatmiserneo.async_setup_entry") as mock_setup_entry,
    ):
        mock_hub_instance = mock_neohub_class.return_value
        mock_hub_instance.firmware = AsyncMock(
            return_value=None
        )  # Assume firmware returns nothing specific; adjust if it returns data
        mock_hub_instance.mac_address = (
            None  # "00:11:22:33:44:55"  # Fake MAC for unique_id
        )
        mock_hub_instance.disconnect = AsyncMock(return_value=None)
        mock_hub_instance.get_all_live_data = AsyncMock(return_value=None)

        # Simulate user input (adjust fields to match your config_flow)
        result = await hass.config_entries.flow.async_configure(
            legacy_conn_form["flow_id"], {"host": "test-hub"}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "test-hub:4242"  # Adjust title if needed
        assert result["data"] == {"host": "test-hub", "port": 4242}
        assert result["result"].unique_id == "test-hub:4242"
        assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.asyncio
async def test_create_manual_websocket(
    hass: HomeAssistant,  # , config: dict[str, Any], options: dict[str, Any]
) -> None:
    """Test that the form is served with no input."""
    menu_step = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert menu_step["type"] is FlowResultType.MENU
    assert menu_step["step_id"] == "choose_discovery_method"

    conn_menu_step = await hass.config_entries.flow.async_configure(
        menu_step["flow_id"],
        {"next_step_id": CONF_DISCOVERY_METHOD_MANUAL},
    )

    assert conn_menu_step["type"] is FlowResultType.MENU
    assert conn_menu_step["step_id"] == "choose_conn_method"

    legacy_conn_form = await hass.config_entries.flow.async_configure(
        conn_menu_step["flow_id"],
        {"next_step_id": CONF_CONN_METHOD_WEBSOCKET},
    )

    assert legacy_conn_form["type"] is FlowResultType.FORM
    assert legacy_conn_form["step_id"] == CONF_CONN_METHOD_WEBSOCKET

    # Mock the NeoHub to simulate successful connection
    with (
        patch("custom_components.heatmiserneo.config_flow.NeoHub") as mock_neohub_class,
        patch("custom_components.heatmiserneo.async_setup_entry") as mock_setup_entry,
    ):
        mock_hub_instance = mock_neohub_class.return_value
        mock_hub_instance.firmware = AsyncMock(
            return_value=None
        )  # Assume firmware returns nothing specific; adjust if it returns data
        mock_hub_instance.mac_address = "00:11:22:33:44:55"  # Fake MAC for unique_id
        mock_hub_instance.disconnect = AsyncMock(return_value=None)
        mock_hub_instance.get_all_live_data = AsyncMock(return_value=None)

        # Simulate user input (adjust fields to match your config_flow)
        result = await hass.config_entries.flow.async_configure(
            legacy_conn_form["flow_id"], {"host": "test-hub", "api_token": "123456789"}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "test-hub:4243"  # Adjust title if needed
        assert result["data"] == {
            "host": "test-hub",
            "port": 4243,
            "api_token": "123456789",
        }
        assert result["result"].unique_id == "00:11:22:33:44:55"
        assert len(mock_setup_entry.mock_calls) == 1


async def test_zeroconf_discovery(
    hass: HomeAssistant,
) -> None:
    """Test zeroconf discovery."""
    conn_menu_step = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=ZEROCONF_DISCOVERY,
    )

    assert conn_menu_step["type"] is FlowResultType.MENU
    assert conn_menu_step["step_id"] == "choose_conn_method"

    legacy_conn_form = await hass.config_entries.flow.async_configure(
        conn_menu_step["flow_id"],
        {"next_step_id": CONF_CONN_METHOD_WEBSOCKET},
    )

    assert legacy_conn_form["type"] is FlowResultType.FORM
    assert legacy_conn_form["step_id"] == CONF_CONN_METHOD_WEBSOCKET

    # Mock the NeoHub to simulate successful connection
    with (
        patch("custom_components.heatmiserneo.config_flow.NeoHub") as mock_neohub_class,
        patch("custom_components.heatmiserneo.async_setup_entry") as mock_setup_entry,
    ):
        mock_hub_instance = mock_neohub_class.return_value
        mock_hub_instance.firmware = AsyncMock(
            return_value=None
        )  # Assume firmware returns nothing specific; adjust if it returns data
        mock_mac = ZEROCONF_DISCOVERY.properties.get("id")
        mock_hub_instance.mac_address = mock_mac  # Fake MAC for unique_id
        mock_hub_instance.disconnect = AsyncMock(return_value=None)
        mock_hub_instance.get_all_live_data = AsyncMock(return_value=None)

        # Simulate user input (adjust fields to match your config_flow)
        result = await hass.config_entries.flow.async_configure(
            legacy_conn_form["flow_id"],
            {"host": ZEROCONF_DISCOVERY.host, "api_token": "123456789"},
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert (
            result["title"] == f"{ZEROCONF_DISCOVERY.host}:4243"
        )  # Adjust title if needed
        assert result["data"] == {
            "host": ZEROCONF_DISCOVERY.host,
            "port": 4243,
            "api_token": "123456789",
        }
        assert result["result"].unique_id == mock_mac
        assert len(mock_setup_entry.mock_calls) == 1


async def test_zeroconf_discovery_connect_mismatch(
    hass: HomeAssistant,
) -> None:
    """Test zeroconf discovery."""
    conn_menu_step = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=ZEROCONF_DISCOVERY,
    )

    assert conn_menu_step["type"] is FlowResultType.MENU
    assert conn_menu_step["step_id"] == "choose_conn_method"

    legacy_conn_form = await hass.config_entries.flow.async_configure(
        conn_menu_step["flow_id"],
        {"next_step_id": CONF_CONN_METHOD_WEBSOCKET},
    )

    assert legacy_conn_form["type"] is FlowResultType.FORM
    assert legacy_conn_form["step_id"] == CONF_CONN_METHOD_WEBSOCKET

    # Mock the NeoHub to simulate successful connection
    with (
        patch("custom_components.heatmiserneo.config_flow.NeoHub") as mock_neohub_class,
    ):
        mock_hub_instance = mock_neohub_class.return_value
        mock_hub_instance.firmware = AsyncMock(
            return_value=None
        )  # Assume firmware returns nothing specific; adjust if it returns data
        mock_mac = "00:11:22:33:44:55"
        mock_hub_instance.mac_address = mock_mac  # Fake MAC for unique_id
        mock_hub_instance.disconnect = AsyncMock(return_value=None)
        mock_hub_instance.get_all_live_data = AsyncMock(return_value=None)

        # Simulate user input (adjust fields to match your config_flow)
        result = await hass.config_entries.flow.async_configure(
            legacy_conn_form["flow_id"],
            {"host": ZEROCONF_DISCOVERY.host, "api_token": "123456789"},
        )
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "connect_mismatch"


async def test_integration_discovery_using_legacy(
    hass: HomeAssistant,
) -> None:
    """Test integration discovery."""
    conn_menu_step = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_INTEGRATION_DISCOVERY},
        data=INTEGRATION_DISCOVERY,
    )

    assert conn_menu_step["type"] is FlowResultType.MENU
    assert conn_menu_step["step_id"] == "choose_conn_method"

    legacy_conn_form = await hass.config_entries.flow.async_configure(
        conn_menu_step["flow_id"],
        {"next_step_id": CONF_CONN_METHOD_LEGACY},
    )

    assert legacy_conn_form["type"] is FlowResultType.FORM
    assert legacy_conn_form["step_id"] == CONF_CONN_METHOD_LEGACY

    # Mock the NeoHub to simulate successful connection
    with (
        patch("custom_components.heatmiserneo.config_flow.NeoHub") as mock_neohub_class,
        patch("custom_components.heatmiserneo.async_setup_entry") as mock_setup_entry,
    ):
        mock_hub_instance = mock_neohub_class.return_value
        mock_hub_instance.firmware = AsyncMock(
            return_value=None
        )  # Assume firmware returns nothing specific; adjust if it returns data
        mock_mac = ZEROCONF_DISCOVERY.properties.get("id")
        mock_hub_instance.mac_address = None
        mock_hub_instance.disconnect = AsyncMock(return_value=None)
        mock_hub_instance.get_all_live_data = AsyncMock(return_value=None)

        # Simulate user input (adjust fields to match your config_flow)
        result = await hass.config_entries.flow.async_configure(
            legacy_conn_form["flow_id"],
            {"host": ZEROCONF_DISCOVERY.host},
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert (
            result["title"] == f"{ZEROCONF_DISCOVERY.host}:4242"
        )  # Adjust title if needed
        assert result["data"] == {
            "host": ZEROCONF_DISCOVERY.host,
            "port": 4242,
        }
        assert result["result"].unique_id == mock_mac
        assert len(mock_setup_entry.mock_calls) == 1


async def test_options_flow(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Test options flow."""
    with (
        patch("custom_components.heatmiserneo.config_flow.NeoHub") as mock_neohub,
        patch("neohubapi.neostat.NeoStat") as mock_device,
    ):
        mock_neohub.get_all_live_data = AsyncMock(
            return_value={
                ATTR_LIVE: [],
                ATTR_DEVICES: [mock_device],
                ATTR_SYSTEM: SimpleNamespace(
                    {
                        "CORF": "C",
                        "GLOBAL_SYSTEM_TYPE": GlobalSystemType.HEAT_ONLY,
                    }
                ),
                ATTR_PROFILES: [],
                ATTR_PROFILES_0: [],
                ATTR_TIMER_PROFILES: [],
                ATTR_TIMER_PROFILES_0: [],
            }
        )
        mock_neohub.target_temperature_step = AsyncMock(return_value=0.5)
        coordinator = HeatmiserNeoCoordinator(hass, config_entry, mock_neohub)
        await coordinator.async_refresh()
        config_entry.runtime_data = HeatmiserNeoData(mock_neohub, coordinator)

        result = await hass.config_entries.options.async_init(config_entry.entry_id)

        assert result["type"] is FlowResultType.MENU
        assert result["step_id"] == "choose_options"

        defaults_form = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"next_step_id": CONF_DEFAULTS},
        )

        assert defaults_form["type"] is FlowResultType.FORM
        assert defaults_form["step_id"] == CONF_DEFAULTS

        UPDATE_OPTIONS = {
            CONF_THERMOSTAT_OPTIONS: {
                CONF_STAT_HOLD_TEMP: 2,
                CONF_STAT_HOLD_DURATION: {"minutes": 30},
                CONF_STAT_MIN_TEMPERATURE: 10,
                CONF_STAT_MAX_TEMPERATURE: 40,
            },
            CONF_TIMER_OPTIONS: {CONF_TIMER_HOLD_DURATION: {"minutes": 45}},
        }

        result2 = await hass.config_entries.options.async_configure(
            defaults_form["flow_id"], UPDATE_OPTIONS
        )
        assert result2["type"] is FlowResultType.CREATE_ENTRY
        assert result2["data"] == {
            CONF_DEFAULTS: {
                CONF_THERMOSTAT_OPTIONS: {
                    CONF_STAT_HOLD_TEMP: 2.0,
                    CONF_STAT_HOLD_DURATION: 30,
                    CONF_STAT_MIN_TEMPERATURE: 10.0,
                    CONF_STAT_MAX_TEMPERATURE: 40.0,
                },
                CONF_TIMER_OPTIONS: {CONF_TIMER_HOLD_DURATION: 45},
            },
            CONF_HVAC_MODES: {"TEST_HC": {AvailableMode.HEAT}},
        }
        await hass.async_block_till_done()
