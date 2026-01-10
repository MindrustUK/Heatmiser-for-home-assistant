# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
"""Test the heatmiserneo config flow."""

import asyncio
from ipaddress import ip_address
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, patch

from custom_components.heatmiserneo.const import (
    CONF_CONN_METHOD_LEGACY,
    CONF_CONN_METHOD_WEBSOCKET,
    CONF_DEFAULTS,
    CONF_DISCOVERY_METHOD_AUTO_CONNECT,
    CONF_DISCOVERY_METHOD_HUBSEEK,
    CONF_DISCOVERY_METHOD_MANUAL,
    CONF_HVAC_MODES,
    CONF_PAIRING,
    CONF_PAIRING_REPEATER,
    CONF_STAT_HOLD_DURATION,
    CONF_STAT_HOLD_TEMP,
    CONF_STAT_MAX_TEMPERATURE,
    CONF_STAT_MIN_TEMPERATURE,
    CONF_THERMOSTAT_OPTIONS,
    CONF_TIMER_HOLD_DURATION,
    CONF_TIMER_OPTIONS,
    DISCOVER_AUTO_CONNECT_TIMEOUT,
    DOMAIN,
    AvailableMode,
    GlobalSystemType,
)
from custom_components.heatmiserneo.coordinator import (
    HeatmiserNeoCoordinator,
    HeatmiserNeoData,
)
from neohubapi.discovery import NeoHubConnectDetails, NeoHubDetails
from neohubapi.neohub import (
    ATTR_DEVICES,
    ATTR_LIVE,
    ATTR_PROFILES,
    ATTR_PROFILES_0,
    ATTR_SYSTEM,
    ATTR_TIMER_PROFILES,
    ATTR_TIMER_PROFILES_0,
    NeoHubConnectionError,
)
import pytest
from pytest_homeassistant.common import MockConfigEntry

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
        "id": "xx:xx:xx:xx:xx:xx",
    },
)

INTEGRATION_DISCOVERY: DiscoveryInfoType = {
    "mac_address": "aa:bb:cc:dd:ee:ff",
    "ip_address": "192.168.1.100",
}


def _set_options_runtime_data(
    config_entry: ConfigEntry, devices: dict[str, SimpleNamespace] | None = None
) -> SimpleNamespace:
    """Provide the runtime data required by the options flow."""
    system_data = SimpleNamespace(
        CORF="C", GLOBAL_SYSTEM_TYPE=GlobalSystemType.HEAT_ONLY
    )
    coordinator = SimpleNamespace(
        data=(devices or {}, {"system": system_data}),
        system_data=system_data,
        async_request_refresh=AsyncMock(),
        hub=SimpleNamespace(
            target_temperature_step=AsyncMock(return_value=0.5),
            permit_join=AsyncMock(),
            permit_repeater_join=AsyncMock(),
        ),
    )
    config_entry.runtime_data = SimpleNamespace(coordinator=coordinator)
    return coordinator


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
        patch(
            "custom_components.heatmiserneo.async_setup_entry", return_value=None
        ) as mock_setup_entry,
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
        patch(
            "custom_components.heatmiserneo.async_setup_entry", return_value=None
        ) as mock_setup_entry,
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
    with (
        patch(
            "custom_components.heatmiserneo.config_flow.async_discover_device",
            AsyncMock(
                return_value=SimpleNamespace(
                    mac_address=INTEGRATION_DISCOVERY["mac_address"]
                )
            ),
        ),
    ):
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
        patch(
            "custom_components.heatmiserneo.async_setup_entry", return_value=None
        ) as mock_setup_entry,
    ):
        mock_hub_instance = mock_neohub_class.return_value
        mock_hub_instance.firmware = AsyncMock(
            return_value=None
        )  # Assume firmware returns nothing specific; adjust if it returns data
        mock_mac = INTEGRATION_DISCOVERY["mac_address"]
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
    with (
        patch(
            "custom_components.heatmiserneo.config_flow.async_discover_device",
            AsyncMock(
                return_value=SimpleNamespace(
                    mac_address=INTEGRATION_DISCOVERY["mac_address"]
                )
            ),
        ),
    ):
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

    # Mock the NeoHub to simulate successful connection
    with (
        patch("custom_components.heatmiserneo.config_flow.NeoHub") as mock_neohub_class,
        patch(
            "custom_components.heatmiserneo.async_setup_entry", return_value=None
        ) as mock_setup_entry,
    ):
        mock_hub_instance = mock_neohub_class.return_value
        mock_hub_instance.firmware = AsyncMock(
            side_effect=[NeoHubConnectionError(), None]
        )
        mock_mac = INTEGRATION_DISCOVERY["mac_address"]
        mock_hub_instance.mac_address = None
        mock_hub_instance.disconnect = AsyncMock(return_value=None)
        mock_hub_instance.get_all_live_data = AsyncMock(return_value=None)

        legacy_conn_form = await hass.config_entries.flow.async_configure(
            conn_menu_step["flow_id"],
            {"next_step_id": CONF_CONN_METHOD_LEGACY},
        )

        assert legacy_conn_form["type"] is FlowResultType.FORM
        assert legacy_conn_form["step_id"] == CONF_CONN_METHOD_LEGACY
        assert legacy_conn_form["errors"] == {"base": "cannot_connect"}

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


@pytest.mark.parametrize(
    ("direct_link_token", "expected_port"),
    [(None, 4242), ("direct-link-token", 4243)],
    ids=["legacy", "websocket"],
)
async def test_auto_connect(
    hass: HomeAssistant, direct_link_token: str | None, expected_port: int
) -> None:
    """Test successful auto-connect discovery."""
    connect_details = NeoHubConnectDetails(
        mac_address="aa:bb:cc:dd:ee:ff",
        ip_address="192.168.1.50",
        token="token",
        version="1",
        direct_link_token=direct_link_token,
    )
    with (
        patch(
            "custom_components.heatmiserneo.config_flow.async_discover_device_connection_details",
            AsyncMock(return_value=connect_details),
        ),
        patch("custom_components.heatmiserneo.config_flow.NeoHub") as mock_neohub,
        patch(
            "custom_components.heatmiserneo.async_setup_entry", return_value=None
        ) as mock_setup_entry,
    ):
        mock_hub = mock_neohub.return_value
        mock_hub.firmware = AsyncMock(return_value=None)
        mock_hub.mac_address = None
        mock_hub.disconnect = AsyncMock()

        menu = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            menu["flow_id"],
            {"next_step_id": CONF_DISCOVERY_METHOD_AUTO_CONNECT},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    expected_data = {"host": "192.168.1.50", "port": expected_port}
    if direct_link_token:
        expected_data["api_token"] = direct_link_token
    assert result["data"] == expected_data
    assert result["result"].unique_id == "aa:bb:cc:dd:ee:ff"
    mock_neohub.assert_called_once_with(
        "192.168.1.50",
        expected_port,
        token=direct_link_token,
        connection_ttl=ANY,
    )
    mock_hub.disconnect.assert_awaited_once()
    assert len(mock_setup_entry.mock_calls) == 1


async def test_auto_connect_without_device_aborts(
    hass: HomeAssistant,
) -> None:
    """Test auto-connect aborts when no device is found."""
    with patch(
        "custom_components.heatmiserneo.config_flow.async_discover_device_connection_details",
        AsyncMock(return_value=None),
    ):
        menu = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            menu["flow_id"],
            {"next_step_id": CONF_DISCOVERY_METHOD_AUTO_CONNECT},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "auto_connect_timeout"


async def test_auto_connect_waits_for_discovery(
    hass: HomeAssistant,
) -> None:
    """Test auto-connect displays progress while discovery is pending."""
    discovery_complete = asyncio.Event()

    async def wait_for_discovery(_hass: HomeAssistant) -> None:
        await discovery_complete.wait()

    with patch(
        "custom_components.heatmiserneo.config_flow.async_discover_device_connection_details",
        side_effect=wait_for_discovery,
    ):
        menu = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        progress = await hass.config_entries.flow.async_configure(
            menu["flow_id"],
            {"next_step_id": CONF_DISCOVERY_METHOD_AUTO_CONNECT},
        )
        assert progress["type"] is FlowResultType.SHOW_PROGRESS
        assert progress["progress_action"] == "press_connect_button"
        assert progress["description_placeholders"]["timeout"] == str(
            DISCOVER_AUTO_CONNECT_TIMEOUT
        )

        discovery_complete.set()
        await hass.async_block_till_done()
        result = await hass.config_entries.flow.async_configure(progress["flow_id"])

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "auto_connect_timeout"


async def test_auto_connect_aborts_when_mac_does_not_match_discovery(
    hass: HomeAssistant,
) -> None:
    """Test auto-connect aborts when its MAC differs from zeroconf discovery."""
    connect_details = NeoHubConnectDetails(
        mac_address="11:22:33:44:55:66",
        ip_address=ZEROCONF_DISCOVERY.host,
        token="token",
        version="1",
        direct_link_token=None,
    )
    with (
        patch(
            "custom_components.heatmiserneo.config_flow.async_discover_device",
            AsyncMock(
                return_value=SimpleNamespace(
                    mac_address=INTEGRATION_DISCOVERY["mac_address"]
                )
            ),
        ),
        patch(
            "custom_components.heatmiserneo.config_flow.async_discover_device_connection_details",
            AsyncMock(return_value=connect_details),
        ),
    ):
        menu = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_ZEROCONF},
            data=ZEROCONF_DISCOVERY,
        )
        result = await hass.config_entries.flow.async_configure(
            menu["flow_id"],
            {"next_step_id": CONF_DISCOVERY_METHOD_AUTO_CONNECT},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "auto_connect_mismatch"


async def test_hubseek_aborts_when_no_devices_are_discovered(
    hass: HomeAssistant,
) -> None:
    """Test Hubseek aborts when it finds no devices."""
    with patch(
        "custom_components.heatmiserneo.config_flow.async_discover_devices",
        AsyncMock(return_value=[]),
    ):
        menu = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            menu["flow_id"],
            {"next_step_id": CONF_DISCOVERY_METHOD_HUBSEEK},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_discovered"


async def test_hubseek_aborts_when_only_configured_devices_are_discovered(
    hass: HomeAssistant,
) -> None:
    """Test Hubseek excludes already configured devices."""
    device = NeoHubDetails("aa:bb:cc:dd:ee:ff", "192.168.1.50")
    MockConfigEntry(
        domain=DOMAIN,
        unique_id=device.mac_address,
        data={"host": device.ip_address, "port": 4242},
    ).add_to_hass(hass)
    with patch(
        "custom_components.heatmiserneo.config_flow.async_discover_devices",
        AsyncMock(return_value=[device]),
    ):
        menu = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            menu["flow_id"],
            {"next_step_id": CONF_DISCOVERY_METHOD_HUBSEEK},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_new_devices_discovered"


async def test_hubseek_selects_discovered_device(
    hass: HomeAssistant,
) -> None:
    """Test selecting a discovered device opens connection-method selection."""
    device = NeoHubDetails("aa:bb:cc:dd:ee:ff", "192.168.1.50")
    with patch(
        "custom_components.heatmiserneo.config_flow.async_discover_devices",
        AsyncMock(return_value=[device]),
    ):
        menu = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        form = await hass.config_entries.flow.async_configure(
            menu["flow_id"],
            {"next_step_id": CONF_DISCOVERY_METHOD_HUBSEEK},
        )

    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == CONF_DISCOVERY_METHOD_HUBSEEK
    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], {"device": device.mac_address}
    )

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "choose_conn_method"


async def test_manual_connection_aborts_duplicate_unique_id(
    hass: HomeAssistant,
) -> None:
    """Test manual setup aborts before connecting when the unique ID exists."""
    host = "192.168.1.50"
    MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{host}:4242",
        data={"host": host, "port": 4242},
    ).add_to_hass(hass)
    with patch("custom_components.heatmiserneo.config_flow.NeoHub") as mock_neohub:
        menu = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        conn_menu = await hass.config_entries.flow.async_configure(
            menu["flow_id"],
            {"next_step_id": CONF_DISCOVERY_METHOD_MANUAL},
        )
        form = await hass.config_entries.flow.async_configure(
            conn_menu["flow_id"],
            {"next_step_id": CONF_CONN_METHOD_LEGACY},
        )
        result = await hass.config_entries.flow.async_configure(
            form["flow_id"], {"host": host}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    mock_neohub.assert_not_called()


async def test_manual_connection_aborts_duplicate_host(
    hass: HomeAssistant,
) -> None:
    """Test manual setup detects a configured host with a different unique ID."""
    host = "192.168.1.50"
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="another-device",
        data={"host": host, "port": 4242},
    ).add_to_hass(hass)
    with patch("custom_components.heatmiserneo.config_flow.NeoHub") as mock_neohub:
        mock_hub = mock_neohub.return_value
        mock_hub.firmware = AsyncMock(return_value=None)
        mock_hub.mac_address = None
        mock_hub.disconnect = AsyncMock()

        menu = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        conn_menu = await hass.config_entries.flow.async_configure(
            menu["flow_id"],
            {"next_step_id": CONF_DISCOVERY_METHOD_MANUAL},
        )
        form = await hass.config_entries.flow.async_configure(
            conn_menu["flow_id"],
            {"next_step_id": CONF_CONN_METHOD_LEGACY},
        )
        result = await hass.config_entries.flow.async_configure(
            form["flow_id"], {"host": host}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    mock_hub.disconnect.assert_awaited_once()


@pytest.mark.parametrize("entry_updated", [True, False], ids=["updated", "unchanged"])
async def test_integration_discovery_updates_existing_entry(
    hass: HomeAssistant, entry_updated: bool
) -> None:
    """Test discovery updates an existing entry and reloads only when needed."""
    device = NeoHubDetails("aa:bb:cc:dd:ee:ff", "192.168.1.50")
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=device.mac_address,
        data={"host": "192.168.1.50", "port": 4242},
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.heatmiserneo.config_flow.async_update_entry_from_discovery",
            return_value=entry_updated,
        ) as mock_update,
        patch.object(hass.config_entries, "async_schedule_reload") as mock_reload,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_INTEGRATION_DISCOVERY},
            data={
                "mac_address": device.mac_address,
                "ip_address": device.ip_address,
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    mock_update.assert_called_once_with(hass, entry, device)
    assert mock_reload.call_count == entry_updated


async def test_integration_discovery_aborts_matching_flow(
    hass: HomeAssistant,
) -> None:
    """Test a second discovery for the same host is aborted."""
    first = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_INTEGRATION_DISCOVERY},
        data={"mac_address": "aa:bb:cc:dd:ee:ff", "ip_address": "192.168.1.50"},
    )
    assert first["type"] is FlowResultType.MENU

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_INTEGRATION_DISCOVERY},
        data={"mac_address": "11:22:33:44:55:66", "ip_address": "192.168.1.50"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_in_progress"


async def test_zeroconf_discovery_falls_back_to_property_mac(
    hass: HomeAssistant,
) -> None:
    """Test zeroconf discovery uses the advertised MAC when lookup fails."""
    discovery = ZeroconfServiceInfo(
        ip_address=ip_address("192.168.1.100"),
        ip_addresses=[ip_address("192.168.1.100")],
        hostname="neohub.local.",
        name="heatmiser neohub*",
        port=80,
        type="_hap._tcp.local.",
        properties={"id": "00:11:22:33:44:55"},
    )
    with patch(
        "custom_components.heatmiserneo.config_flow.async_discover_device",
        AsyncMock(return_value=None),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_ZEROCONF},
            data=discovery,
        )

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "choose_conn_method"


async def test_options_menu_hides_hvac_modes_without_hc_devices(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Test HVAC mode options are hidden when there are no eligible devices."""
    _set_options_runtime_data(config_entry)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.MENU
    assert CONF_HVAC_MODES not in result["menu_options"]


@pytest.mark.parametrize(
    ("selected_modes", "expected_modes"),
    [
        ([], {"TEST_HC": [AvailableMode.HEAT.value]}),
        ([AvailableMode.VENT.value], {}),
    ],
    ids=["mandatory-heat", "remove-full-system-override"],
)
async def test_options_hvac_modes(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    selected_modes: list[str],
    expected_modes: dict[str, list[str]],
) -> None:
    """Test HVAC mode overrides include mandatory modes and can be removed."""
    device = SimpleNamespace(device_type=8, time_clock_mode=False)
    _set_options_runtime_data(config_entry, {"TEST_HC": device})
    menu = await hass.config_entries.options.async_init(config_entry.entry_id)
    form = await hass.config_entries.options.async_configure(
        menu["flow_id"], {"next_step_id": CONF_HVAC_MODES}
    )
    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == CONF_HVAC_MODES

    result = await hass.config_entries.options.async_configure(
        form["flow_id"], {"TEST_HC": selected_modes}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HVAC_MODES] == expected_modes


async def test_pairing_starts_device_join(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Test pairing starts device join without waiting on the network."""
    _set_options_runtime_data(config_entry)
    coordinator = config_entry.runtime_data.coordinator
    loop_times = iter((0.0, 0.0, 10.0))
    fake_loop = SimpleNamespace(time=lambda: next(loop_times))
    fake_asyncio = SimpleNamespace(
        get_running_loop=lambda: fake_loop, sleep=AsyncMock()
    )

    async def add_device() -> None:
        coordinator.data = (
            {"New thermostat": object()},
            coordinator.data[1],
        )

    coordinator.async_request_refresh.side_effect = add_device
    with (
        patch("custom_components.heatmiserneo.config_flow.asyncio", fake_asyncio),
        patch.object(
            hass.config_entries, "async_schedule_reload"
        ) as mock_schedule_reload,
    ):
        menu = await hass.config_entries.options.async_init(config_entry.entry_id)
        advanced = await hass.config_entries.options.async_configure(
            menu["flow_id"], {"next_step_id": "choose_advanced"}
        )
        pairing = await hass.config_entries.options.async_configure(
            advanced["flow_id"], {"next_step_id": CONF_PAIRING}
        )
        assert pairing["type"] is FlowResultType.FORM
        pairing = await hass.config_entries.options.async_configure(
            pairing["flow_id"], {"name": "New thermostat"}
        )
        result = pairing

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "device_added"
    coordinator.hub.permit_join.assert_awaited_once_with(
        name="New thermostat", timeout_s=120
    )
    coordinator.async_request_refresh.assert_awaited_once()
    fake_asyncio.sleep.assert_awaited_once_with(1.2)
    mock_schedule_reload.assert_called_once_with(config_entry.entry_id)


async def test_pairing_starts_repeater_join(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Test repeater pairing starts without waiting on the network."""
    _set_options_runtime_data(config_entry)
    coordinator = config_entry.runtime_data.coordinator
    loop_times = iter((0.0, 0.0, 120.0))
    fake_loop = SimpleNamespace(time=lambda: next(loop_times))
    fake_asyncio = SimpleNamespace(
        get_running_loop=lambda: fake_loop, sleep=AsyncMock()
    )
    with patch("custom_components.heatmiserneo.config_flow.asyncio", fake_asyncio):
        menu = await hass.config_entries.options.async_init(config_entry.entry_id)
        advanced = await hass.config_entries.options.async_configure(
            menu["flow_id"], {"next_step_id": "choose_advanced"}
        )
        pairing = await hass.config_entries.options.async_configure(
            advanced["flow_id"], {"next_step_id": CONF_PAIRING_REPEATER}
        )
        result = pairing

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "repeater_add_failed"
    coordinator.hub.permit_repeater_join.assert_awaited_once_with(120)
    coordinator.async_request_refresh.assert_awaited_once()
    fake_asyncio.sleep.assert_awaited_once_with(1.2)


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

        update_options = {
            CONF_THERMOSTAT_OPTIONS: {
                CONF_STAT_HOLD_TEMP: 2,
                CONF_STAT_HOLD_DURATION: {"minutes": 30},
                CONF_STAT_MIN_TEMPERATURE: 10,
                CONF_STAT_MAX_TEMPERATURE: 40,
            },
            CONF_TIMER_OPTIONS: {CONF_TIMER_HOLD_DURATION: {"minutes": 45}},
        }

        result2 = await hass.config_entries.options.async_configure(
            defaults_form["flow_id"], update_options
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
