# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""Heatmiser Neo Sensors via Heatmiser Neo-hub."""

from collections.abc import Callable
from dataclasses import dataclass
import datetime
import logging
from typing import Any

from neohubapi.neohub import NeoHub, NeoStat, ScheduleFormat

from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, Platform, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProfileLevel, TemperatureProfileLevel
from .const import (
    HEATMISER_FAN_SPEED_HA_FAN_MODE,
    HEATMISER_TEMPERATURE_UNIT_HA_UNIT,
    HEATMISER_TYPE_IDS_HC,
    HEATMISER_TYPE_IDS_HOLD,
    HEATMISER_TYPE_IDS_THERMOSTAT,
    HEATMISER_TYPE_IDS_THERMOSTAT_NOT_HC,
    GlobalSystemType,
)
from .coordinator import HeatmiserNeoConfigEntry, HeatmiserNeoCoordinator
from .entity import (
    HeatmiserNeoEntity,
    HeatmiserNeoEntityDescription,
    HeatmiserNeoHubEntity,
    HeatmiserNeoHubEntityDescription,
    async_setup_entities,
    profile_sensor_enabled_by_default,
)
from .helpers import profile_level

_LOGGER = logging.getLogger(__name__)

HOLIDAY_FORMAT = "%a %b %d %H:%M:%S %Y\n"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatmiserNeoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Heatmiser Neo Sensor entities."""
    hub = entry.runtime_data.hub
    coordinator = entry.runtime_data.coordinator

    if coordinator.data is None:
        _LOGGER.error("Coordinator data is None. Cannot set up sensor entities")
        return

    @callback
    def hub_entities():
        return [
            HeatmiserNeoHubSensor(coordinator, hub, description, entry)
            for description in HUB_SENSORS
            if description.setup_filter_fn(coordinator)
        ]

    @callback
    def device_entities(new_devices: list[NeoStat]):
        return [
            HeatmiserNeoSensor(neodevice, coordinator, hub, description, entry)
            for description in SENSORS
            for neodevice in new_devices
            if description.setup_filter_fn(neodevice, coordinator.system_data)
        ]

    await async_setup_entities(
        hass, entry, async_add_entities, Platform.SENSOR, hub_entities, device_entities
    )


@dataclass(frozen=True, kw_only=True)
class HeatmiserNeoSensorEntityDescription(
    HeatmiserNeoEntityDescription, SensorEntityDescription
):
    """Describes a button entity."""

    value_fn: Callable[[HeatmiserNeoEntity], Any]
    unit_of_measurement_fn: Callable[[NeoStat, Any], Any] | None = None


@dataclass(frozen=True, kw_only=True)
class HeatmiserNeoHubSensorEntityDescription(
    HeatmiserNeoHubEntityDescription, SensorEntityDescription
):
    """Describes a button entity."""

    value_fn: Callable[[HeatmiserNeoCoordinator], Any]


SENSORS: tuple[HeatmiserNeoSensorEntityDescription, ...] = (
    HeatmiserNeoSensorEntityDescription(
        key="heatmiser_neo_hold_time_sensor",
        name="Hold Time Remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda device: (
            int(device.data.hold_time.total_seconds() / 60)
            if device.data.hold_on
            else None
        ),
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_HOLD
        ),
    ),
    HeatmiserNeoSensorEntityDescription(
        key="heatmiser_neo_temperature_sensor",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name=None,  # This is the main entity of the device
        value_fn=lambda device: device.data.temperature,
        setup_filter_fn=lambda device, _: device.device_type == 14,
        unit_of_measurement_fn=lambda _, sys_data: (
            HEATMISER_TEMPERATURE_UNIT_HA_UNIT.get(sys_data.CORF, None)
        ),
    ),
    HeatmiserNeoSensorEntityDescription(
        key="heatmiser_neo_stat_current_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        name="Current Temperature",
        value_fn=lambda device: device.data.temperature,
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT
            and not device.time_clock_mode
        ),
        unit_of_measurement_fn=lambda _, sys_data: (
            HEATMISER_TEMPERATURE_UNIT_HA_UNIT.get(sys_data.CORF, None)
        ),
    ),
    HeatmiserNeoSensorEntityDescription(
        key="heatmiser_neo_timer_device_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        name="Device Temperature",
        value_fn=lambda device: device.data.temperature,
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT
            and device.time_clock_mode
        ),
        unit_of_measurement_fn=lambda _, sys_data: (
            HEATMISER_TEMPERATURE_UNIT_HA_UNIT.get(sys_data.CORF, None)
        ),
    ),
    HeatmiserNeoSensorEntityDescription(
        key="heatmiser_neo_stat_floor_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        name="Floor Temperature",
        value_fn=lambda device: device.data.current_floor_temperature,
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT
            and not device.time_clock_mode
            and device.current_floor_temperature < 127
        ),
        unit_of_measurement_fn=lambda _, sys_data: (
            HEATMISER_TEMPERATURE_UNIT_HA_UNIT.get(sys_data.CORF, None)
        ),
    ),
    HeatmiserNeoSensorEntityDescription(
        key="heatmiser_neo_stat_hold_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        name="Hold Temperature",
        value_fn=lambda device: device.data.hold_temp if device.data.hold_on else None,
        setup_filter_fn=lambda device, sys_data: (
            (
                device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT_NOT_HC
                or (
                    device.device_type in HEATMISER_TYPE_IDS_HC
                    and sys_data.GLOBAL_SYSTEM_TYPE != GlobalSystemType.COOL_ONLY
                )
            )
            and not device.time_clock_mode
        ),
        unit_of_measurement_fn=lambda _, sys_data: (
            HEATMISER_TEMPERATURE_UNIT_HA_UNIT.get(sys_data.CORF, None)
        ),
    ),
    HeatmiserNeoSensorEntityDescription(
        key="heatmiser_neo_stat_hold_temp_cool",
        device_class=SensorDeviceClass.TEMPERATURE,
        name="Hold Cooling Temperature",
        value_fn=lambda device: device.data.hold_cool if device.data.hold_on else None,
        setup_filter_fn=lambda device, sys_data: (
            device.device_type in HEATMISER_TYPE_IDS_HC
            and not device.time_clock_mode
            and sys_data.GLOBAL_SYSTEM_TYPE != GlobalSystemType.HEAT_ONLY
        ),
        unit_of_measurement_fn=lambda _, sys_data: (
            HEATMISER_TEMPERATURE_UNIT_HA_UNIT.get(sys_data.CORF, None)
        ),
    ),
    HeatmiserNeoSensorEntityDescription(
        key="heatmiser_neo_stat_hc_fan_speed",
        device_class=SensorDeviceClass.ENUM,
        options=[FAN_OFF, FAN_HIGH, FAN_MEDIUM, FAN_LOW, FAN_AUTO],
        translation_key="fan_speed",
        value_fn=lambda device: (
            FAN_AUTO
            if device.data.fan_control != "Manual"
            else HEATMISER_FAN_SPEED_HA_FAN_MODE.get(device.data.fan_speed, FAN_OFF)
        ),
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_HC and not device.time_clock_mode
        ),
    ),
    HeatmiserNeoSensorEntityDescription(
        key="heatmiser_neo_profile_current_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        name="Profile Current Temperature",
        value_fn=lambda device: _profile_current_temp(
            device.data.active_profile, device
        ),
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT_NOT_HC
            and not device.time_clock_mode
        ),
        unit_of_measurement_fn=lambda _, sys_data: (
            HEATMISER_TEMPERATURE_UNIT_HA_UNIT.get(sys_data.CORF, None)
        ),
        enabled_by_default_fn=profile_sensor_enabled_by_default,
    ),
    HeatmiserNeoSensorEntityDescription(
        key="heatmiser_neo_profile_next_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        name="Profile Next Temperature",
        value_fn=lambda device: _profile_next_temp(device.data.active_profile, device),
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT_NOT_HC
            and not device.time_clock_mode
        ),
        unit_of_measurement_fn=lambda _, sys_data: (
            HEATMISER_TEMPERATURE_UNIT_HA_UNIT.get(sys_data.CORF, None)
        ),
        enabled_by_default_fn=profile_sensor_enabled_by_default,
    ),
    HeatmiserNeoSensorEntityDescription(
        key="heatmiser_neo_profile_next_time",
        name="Profile Next Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda device: _profile_next_time(device.data.active_profile, device),
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT_NOT_HC
        ),
        enabled_by_default_fn=profile_sensor_enabled_by_default,
    ),
)

HUB_SENSORS: tuple[HeatmiserNeoHubSensorEntityDescription, ...] = (
    HeatmiserNeoHubSensorEntityDescription(
        key="heatmiser_neohub_zigbee_channel",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        name="ZigBee Channel",
        value_fn=lambda coordinator: coordinator.system_data.ZIGBEE_CHANNEL,
    ),
    HeatmiserNeoHubSensorEntityDescription(
        key="heatmiser_neohub_holiday_end",
        device_class=SensorDeviceClass.TIMESTAMP,
        name="Away End",
        value_fn=lambda coordinator: _holiday_end(coordinator),
    ),
    HeatmiserNeoHubSensorEntityDescription(
        key="heatmiser_neohub_profile_format",
        device_class=SensorDeviceClass.ENUM,
        options=[e._name_.lower() for e in ScheduleFormat],
        value_fn=lambda coordinator: coordinator.system_data.FORMAT._name_.lower()
        if coordinator.system_data.FORMAT
        else None,
        translation_key="hub_profile_format",
    ),
    HeatmiserNeoHubSensorEntityDescription(
        key="heatmiser_neohub_alt_timer_profile_format",
        device_class=SensorDeviceClass.ENUM,
        options=[e._name_.lower() for e in ScheduleFormat if e != ScheduleFormat.ZERO],
        value_fn=lambda coordinator: coordinator.system_data.ALT_TIMER_FORMAT._name_.lower()
        if coordinator.system_data.ALT_TIMER_FORMAT
        and coordinator.system_data.FORMAT == ScheduleFormat.ZERO
        else None,
        translation_key="hub_profile_alt_timer_format",
    ),
    HeatmiserNeoHubSensorEntityDescription(
        key="heatmiser_neohub_heating_levels",
        device_class=SensorDeviceClass.ENUM,
        options=["4", "6"],
        value_fn=lambda coordinator: str(coordinator.system_data.HEATING_LEVELS),
        translation_key="hub_profile_heating_levels",
    ),
)


class HeatmiserNeoSensor(
    HeatmiserNeoEntity[HeatmiserNeoSensorEntityDescription], SensorEntity
):
    """Heatmiser Neo button entity."""

    def __init__(
        self,
        neostat: NeoStat,
        coordinator: HeatmiserNeoCoordinator,
        hub: NeoHub,
        entity_description: HeatmiserNeoSensorEntityDescription,
        config_entry: HeatmiserNeoConfigEntry,
    ) -> None:
        """Initialize Heatmiser Neo button entity."""
        super().__init__(neostat, coordinator, hub, entity_description, config_entry)

    @property
    def native_value(self):
        """Return the sensors temperature value."""
        return self.entity_description.value_fn(self)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        if self.entity_description.unit_of_measurement_fn:
            return self.entity_description.unit_of_measurement_fn(
                self.data, self.system_data
            )

        return self.entity_description.native_unit_of_measurement


class HeatmiserNeoHubSensor(
    HeatmiserNeoHubEntity[HeatmiserNeoHubSensorEntityDescription], SensorEntity
):
    """Heatmiser Neo button entity."""

    def __init__(
        self,
        coordinator: HeatmiserNeoCoordinator,
        hub: NeoHub,
        entity_description: HeatmiserNeoHubSensorEntityDescription,
        config_entry: HeatmiserNeoConfigEntry,
    ) -> None:
        """Initialize Heatmiser Neo button entity."""
        super().__init__(coordinator, hub, entity_description, config_entry)

    @property
    def native_value(self):
        """Return the sensors temperature value."""
        return self.entity_description.value_fn(self.coordinator)


def _profile_current_temp(profile_id, entity: HeatmiserNeoEntity) -> float | None:
    """Convert a profile id to current temperature."""
    level = profile_level(profile_id, entity.data, entity.coordinator)
    if isinstance(level, TemperatureProfileLevel):
        return level.temperature
    return None


def _profile_next_temp(profile_id, entity: HeatmiserNeoEntity) -> float | None:
    level = _profile_next_level(profile_id, entity)
    if isinstance(level, TemperatureProfileLevel) and level.temperature:
        return level.temperature
    return None


def _profile_next_time(
    profile_id, entity: HeatmiserNeoEntity
) -> datetime.datetime | None:
    level = _profile_next_level(profile_id, entity)
    if not level:
        return None
    device_time = entity.data._data_.TIME
    if len(device_time) == 4:
        device_time = f"0{device_time}"
    profile_time = datetime.datetime.strptime(level.time, "%H:%M")
    tz = entity.coordinator.system_data.TIME_ZONE
    if entity.coordinator.system_data.DST_ON:
        tz = tz + 1
    profile_datetime = datetime.datetime.now().replace(
        hour=profile_time.hour,
        minute=profile_time.minute,
        second=0,
        microsecond=0,
        tzinfo=datetime.timezone(datetime.timedelta(minutes=tz * 60)),
    )
    if level.time < device_time:
        return profile_datetime + datetime.timedelta(days=1)
    return profile_datetime


def _profile_next_level(profile_id, entity: HeatmiserNeoEntity) -> ProfileLevel | None:
    """Convert a profile id to next level."""
    return profile_level(profile_id, entity.data, entity.coordinator, True)


def _holiday_end(coordinator: HeatmiserNeoCoordinator) -> datetime.datetime | None:
    """Convert the holiday end to a datetime."""
    holiday = coordinator.live_data.HUB_HOLIDAY
    holiday_end = coordinator.live_data.HOLIDAY_END

    if not holiday or holiday_end == 0:
        return None

    try:
        parsed_datetime = datetime.datetime.strptime(holiday_end, HOLIDAY_FORMAT)
        return parsed_datetime.replace(
            tzinfo=datetime.timezone(
                datetime.timedelta(minutes=coordinator.system_data.TIME_ZONE * 60)
            )
        )
    except ValueError:
        _LOGGER.exception("Failed to parse hub holiday end - %s", holiday_end)
        return None
