# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
"""Diagnostics support for Heatmiser Neo."""

from __future__ import annotations

import logging
from typing import Any

from neohubapi.neohub import NeoHub, NeoStat

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_TOKEN, CONF_HOST, CONF_TOKEN, CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant

from .coordinator import HeatmiserNeoConfigEntry
from .utils import to_dict

_LOGGER = logging.getLogger(__name__)

TO_REDACT_CONFIG = {CONF_HOST, "title", CONF_UNIQUE_ID, CONF_TOKEN, CONF_API_TOKEN}
TO_REDACT_RAW_DATA = {"PIN_NUMBER"}
TO_REDACT_DEVICES = {"pin_number"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: HeatmiserNeoConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    hub = entry.runtime_data.hub
    coordinator = entry.runtime_data.coordinator

    neo_devices, _ = coordinator.data
    live_data = coordinator.live_data
    system_data = coordinator.system_data
    profiles = coordinator.profiles
    profiles_0 = coordinator.profiles_0
    timer_profiles = coordinator.timer_profiles
    timer_profiles_0 = coordinator.timer_profiles_0
    engineers_data = await hub.get_engineers()
    raw_live_data = await hub.get_live_data()
    raw_live_data = to_dict(raw_live_data)
    raw_live_data["devices"] = [
        async_redact_data(to_dict(dev), TO_REDACT_RAW_DATA)
        for dev in raw_live_data.get("devices", [])
    ]
    devices = await hub.get_devices()
    devices_sns = {device.serial_number for device in neo_devices.values()}
    devices_sns = {n: "REDACTED-SN-" + str(i) for i, n in enumerate(devices_sns)}
    zones = {
        device._data_.ZONE_NAME
        for device in neo_devices.values()
        if hasattr(device._data_, "ZONE_NAME")
    }
    device_list = {z: await retrieve_zone_device_list(z, hub) for z in zones}
    return {
        "config_entry": async_redact_data(entry.as_dict(), TO_REDACT_CONFIG),
        "devices_data": [
            convert_to_dict(device, devices_sns) for device in neo_devices.values()
        ],
        "live_data": to_dict(live_data),
        "system_data": to_dict(system_data),
        "engineers": to_dict(engineers_data),
        "devices": devices.result if devices else None,
        "device_list": device_list,
        "zones": zones,
        "profiles": to_dict(profiles),
        "profiles_0": to_dict(profiles_0),
        "timer_profiles": to_dict(timer_profiles),
        "timer_profiles_0": to_dict(timer_profiles_0),
        "raw_live_data": raw_live_data,
    }


def convert_to_dict(device: NeoStat, device_sns: dict[str, str]) -> dict:
    """Convert a NeoStat entity to a redacted dict."""

    dev_diagnostics = device.__dict__.copy()
    dev_diagnostics["raw_data"] = async_redact_data(
        to_dict(device._data_), TO_REDACT_RAW_DATA
    )
    del dev_diagnostics["_hub"]
    del dev_diagnostics["_data_"]
    dev_diagnostics["serial_number"] = device_sns.get(
        dev_diagnostics.get("serial_number", ""), "REDACTED-SN-UNKNOWN"
    )
    dev_diagnostics["raw_data"]["SERIAL_NUMBER"] = device_sns.get(
        dev_diagnostics["raw_data"].get("SERIAL_NUMBER", ""), "REDACTED-SN-UNKNOWN"
    )
    return async_redact_data(to_dict(dev_diagnostics), TO_REDACT_DEVICES)


async def retrieve_zone_device_list(zone: str, hub: NeoHub):
    """Get device list for each zone."""
    response = await hub._send({"GET_DEVICE_LIST": zone})  # noqa: SLF001
    _LOGGER.debug("Response for GET_DEVICE_LIST on zone %s: %s", zone, response)
    return to_dict(response).get(zone, {})
