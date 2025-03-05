# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""Heatmiser Neo Binary Sensors via Heatmiser Neo-hub."""

from collections.abc import Callable
from dataclasses import dataclass
import datetime
from functools import partial
import logging
from typing import Any

from neohubapi.neohub import NeoHub, NeoStat
import voluptuous as vol

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatmiserNeoConfigEntry
from .const import (
    ATTR_AWAY_END,
    ATTR_AWAY_STATE,
    HEATMISER_TYPE_IDS_AWAY,
    HEATMISER_TYPE_IDS_HOLD,
    HEATMISER_TYPE_IDS_STANDBY,
    HEATMISER_TYPE_IDS_THERMOSTAT,
    HEATMISER_TYPE_IDS_THERMOSTAT_NOT_HC,
    HEATMISER_TYPE_IDS_TIMER,
    SERVICE_HUB_AWAY,
)
from .coordinator import HeatmiserNeoCoordinator
from .entity import (
    HeatmiserNeoEntity,
    HeatmiserNeoEntityDescription,
    HeatmiserNeoHubEntity,
    HeatmiserNeoHubEntityDescription,
    _device_supports_away,
    call_custom_action,
    profile_sensor_enabled_by_default,
)
from .helpers import profile_level, set_away, set_holiday

_LOGGER = logging.getLogger(__name__)


def _dates_only_provided_when_setting_away(
    state_key, end_key
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Verify that all values are of the same type."""

    def validate(obj: dict[str, Any]) -> dict[str, Any]:
        """Test that all keys in the dict have values of the same type."""
        state_val = obj[state_key]
        # start_val = obj.get(start_key)
        end_val = obj.get(end_key)
        if not state_val:
            # if start_val:
            #     raise vol.Invalid(
            #         "Start date should only be specified if setting away."
            #     )
            if end_val:
                raise vol.Invalid("End date should only be specified if setting away.")
        return obj

    return validate


SET_AWAY_MODE_SCHEMA = vol.Schema(
    vol.All(
        cv.make_entity_service_schema(
            {
                vol.Required(ATTR_AWAY_STATE, default=False): cv.boolean,
                # vol.Optional(ATTR_AWAY_START): cv.datetime,
                vol.Optional(ATTR_AWAY_END): cv.datetime,
            }
        ),
        _dates_only_provided_when_setting_away(ATTR_AWAY_STATE, ATTR_AWAY_END),
    )
)


async def async_set_away_mode(entity: HeatmiserNeoEntity, service_call: ServiceCall):
    """Set away mode on the hub."""
    state = service_call.data[ATTR_AWAY_STATE]
    holiday = None
    away = None
    if not state:
        if entity.coordinator.live_data.HUB_AWAY:
            await entity.coordinator.hub.set_away(False)
            away = False
        if entity.coordinator.live_data.HUB_HOLIDAY:
            await entity.coordinator.hub.cancel_holiday()
            holiday = False
    else:
        end_date = service_call.data.get(ATTR_AWAY_END)
        if end_date:
            if entity.coordinator.live_data.HUB_AWAY:
                await entity.coordinator.hub.set_away(False)
                away = False

            await entity.coordinator.hub.set_holiday(
                datetime.datetime.now() - datetime.timedelta(days=1), end_date
            )
            holiday = True
        else:
            if entity.coordinator.live_data.HUB_HOLIDAY:
                await entity.coordinator.hub.cancel_holiday()
                holiday = False
            await entity.coordinator.hub.set_away(True)
            away = True
    if away is not None:
        entity.coordinator.update_in_memory_state(
            partial(set_away, away),
            _device_supports_away,
        )
        entity.coordinator.live_data.HUB_AWAY = away
    if holiday is not None:
        entity.coordinator.update_in_memory_state(
            partial(set_holiday, holiday),
            _device_supports_away,
        )
        entity.coordinator.live_data.HUB_HOLIDAY = holiday


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatmiserNeoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Heatmiser Neo Binary Sensor entities."""
    hub = entry.runtime_data.hub
    coordinator = entry.runtime_data.coordinator

    if coordinator.data is None:
        _LOGGER.error("Coordinator data is None. Cannot set up sensor entities")
        return

    neo_devices, _ = coordinator.data
    system_data = coordinator.system_data

    _LOGGER.info("Adding Neo Binary Sensors")

    async_add_entities(
        HeatmiserNeoHubBinarySensor(coordinator, hub, description, entry)
        for description in HUB_BINARY_SENSORS
        if description.setup_filter_fn(coordinator)
    )

    async_add_entities(
        HeatmiserNeoBinarySensor(neodevice, coordinator, hub, description, entry)
        for description in BINARY_SENSORS
        for neodevice in neo_devices.values()
        if description.setup_filter_fn(neodevice, system_data)
    )

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_HUB_AWAY,
        SET_AWAY_MODE_SCHEMA,
        call_custom_action,
    )


@dataclass(frozen=True, kw_only=True)
class HeatmiserNeoBinarySensorEntityDescription(
    HeatmiserNeoEntityDescription, BinarySensorEntityDescription
):
    """Describes a button entity."""

    value_fn: Callable[[HeatmiserNeoEntity], bool]


@dataclass(frozen=True, kw_only=True)
class HeatmiserNeoHubBinarySensorEntityDescription(
    HeatmiserNeoHubEntityDescription, BinarySensorEntityDescription
):
    """Describes a button entity."""

    value_fn: Callable[[HeatmiserNeoCoordinator], bool]


BINARY_SENSORS: tuple[HeatmiserNeoBinarySensorEntityDescription, ...] = (
    HeatmiserNeoBinarySensorEntityDescription(
        key="device_offline_sensor",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        availability_fn=lambda _: True,
        value_fn=lambda device: not device.data.offline,
    ),
    HeatmiserNeoBinarySensorEntityDescription(
        key="heatmiser_neo_contact_sensor",
        device_class=BinarySensorDeviceClass.OPENING,
        name=None,  # This is the main entity of the device
        value_fn=lambda device: bool(device.data.window_open),
        setup_filter_fn=lambda device, _: device.device_type == 5,
    ),
    HeatmiserNeoBinarySensorEntityDescription(
        key="heatmiser_neo_device_hold_active",
        entity_category=EntityCategory.DIAGNOSTIC,
        name="Hold Active",
        value_fn=lambda device: device.data.hold_on,
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_HOLD
        ),
    ),
    HeatmiserNeoBinarySensorEntityDescription(
        key="heatmiser_neo_battery_level_sensor",
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: device.data.low_battery,
        setup_filter_fn=lambda device, _: device.battery_powered,
    ),
    HeatmiserNeoBinarySensorEntityDescription(
        key="heatmiser_neo_device_timer_output_active",
        name="Output",
        value_fn=lambda device: device.data.timer_on,
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_TIMER and device.time_clock_mode
        ),
    ),
    HeatmiserNeoBinarySensorEntityDescription(
        key="heatmiser_neo_device_away",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        name="Away",
        value_fn=lambda device: device.data.away or device.data.holiday,
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_AWAY
        ),
    ),
    HeatmiserNeoBinarySensorEntityDescription(
        key="heatmiser_neo_device_standby",
        entity_category=EntityCategory.DIAGNOSTIC,
        name="Standby",
        value_fn=lambda device: device.data.standby,
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_STANDBY
        ),
    ),
    HeatmiserNeoBinarySensorEntityDescription(
        key="heatmiser_neo_floor_limit",
        entity_category=EntityCategory.DIAGNOSTIC,
        name="Floor Limit Reached",
        value_fn=lambda device: device.data.floor_limit,
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT
            and not device.time_clock_mode
            and device.current_floor_temperature < 127
        ),
    ),
    HeatmiserNeoBinarySensorEntityDescription(
        key="heatmiser_neo_temporary_set",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        name="Temporary Set",
        value_fn=lambda device: device.data.temporary_set_flag,
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT
        ),
    ),
    HeatmiserNeoBinarySensorEntityDescription(
        key="heatmiser_neo_profile_current_state",
        name="Profile State",
        value_fn=lambda device: _profile_current_state(
            device.data.active_profile, device
        ),
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT_NOT_HC
            and device.time_clock_mode
        ),
        enabled_by_default_fn=profile_sensor_enabled_by_default,
    ),
)

HUB_BINARY_SENSORS: tuple[HeatmiserNeoHubBinarySensorEntityDescription, ...] = (
    HeatmiserNeoHubBinarySensorEntityDescription(
        key="heatmiser_neohub_dst_on",
        name="DST",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: coordinator.system_data.DST_ON,
    ),
    HeatmiserNeoHubBinarySensorEntityDescription(
        key="heatmiser_neohub_away",
        name="Away",
        value_fn=lambda coordinator: (
            coordinator.live_data.HUB_AWAY or coordinator.live_data.HUB_HOLIDAY
        ),
        custom_functions={SERVICE_HUB_AWAY: async_set_away_mode},
    ),
)


class HeatmiserNeoBinarySensor(HeatmiserNeoEntity, BinarySensorEntity):
    """Heatmiser Neo binary entity."""

    def __init__(
        self,
        neostat: NeoStat,
        coordinator: HeatmiserNeoCoordinator,
        hub: NeoHub,
        entity_description: HeatmiserNeoBinarySensorEntityDescription,
        config_entry: HeatmiserNeoConfigEntry,
    ) -> None:
        """Initialize Heatmiser Neo binary entity."""
        super().__init__(neostat, coordinator, hub, entity_description, config_entry)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.entity_description.value_fn(self)


class HeatmiserNeoHubBinarySensor(HeatmiserNeoHubEntity, BinarySensorEntity):
    """Heatmiser Neo binary entity."""

    def __init__(
        self,
        coordinator: HeatmiserNeoCoordinator,
        hub: NeoHub,
        entity_description: HeatmiserNeoHubBinarySensorEntityDescription,
        config_entry: HeatmiserNeoConfigEntry,
    ) -> None:
        """Initialize Heatmiser Neo binary entity."""
        super().__init__(coordinator, hub, entity_description, config_entry)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.entity_description.value_fn(self.coordinator)


def _profile_current_state(profile_id, entity: HeatmiserNeoEntity) -> bool | None:
    """Convert a profile id to current temperature."""
    level = profile_level(profile_id, entity.data, entity.coordinator)
    if level:
        return level[1]
    return None
