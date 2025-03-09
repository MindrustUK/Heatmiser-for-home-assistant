# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""Heatmiser Neo Sensors via Heatmiser Neo-hub."""

from collections.abc import Callable
from dataclasses import dataclass
import datetime
import json
import logging
from typing import Any

from neohubapi.neohub import NeoHub, NeoStat, ScheduleFormat
import voluptuous as vol

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
from homeassistant.const import ATTR_NAME, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util

from . import HeatmiserNeoConfigEntry
from .const import (
    ATTR_CREATE_MODE,
    ATTR_FRIDAY_OFF_TIMES,
    ATTR_FRIDAY_ON_TIMES,
    ATTR_FRIDAY_TEMPERATURES,
    ATTR_FRIDAY_TIMES,
    ATTR_FRIENDLY_MODE,
    ATTR_MONDAY_OFF_TIMES,
    ATTR_MONDAY_ON_TIMES,
    ATTR_MONDAY_TEMPERATURES,
    ATTR_MONDAY_TIMES,
    ATTR_NAME_NEW,
    ATTR_NAME_OLD,
    ATTR_SATURDAY_OFF_TIMES,
    ATTR_SATURDAY_ON_TIMES,
    ATTR_SATURDAY_TEMPERATURES,
    ATTR_SATURDAY_TIMES,
    ATTR_SUNDAY_OFF_TIMES,
    ATTR_SUNDAY_ON_TIMES,
    ATTR_SUNDAY_TEMPERATURES,
    ATTR_SUNDAY_TIMES,
    ATTR_THURSDAY_OFF_TIMES,
    ATTR_THURSDAY_ON_TIMES,
    ATTR_THURSDAY_TEMPERATURES,
    ATTR_THURSDAY_TIMES,
    ATTR_TUESDAY_OFF_TIMES,
    ATTR_TUESDAY_ON_TIMES,
    ATTR_TUESDAY_TEMPERATURES,
    ATTR_TUESDAY_TIMES,
    ATTR_WEDNESDAY_OFF_TIMES,
    ATTR_WEDNESDAY_ON_TIMES,
    ATTR_WEDNESDAY_TEMPERATURES,
    ATTR_WEDNESDAY_TIMES,
    HEATMISER_FAN_SPEED_HA_FAN_MODE,
    HEATMISER_TEMPERATURE_UNIT_HA_UNIT,
    HEATMISER_TYPE_IDS_HC,
    HEATMISER_TYPE_IDS_HOLD,
    HEATMISER_TYPE_IDS_THERMOSTAT,
    HEATMISER_TYPE_IDS_THERMOSTAT_NOT_HC,
    OPTION_CREATE_MODE_CREATE,
    OPTION_CREATE_MODE_UPDATE,
    OPTIONS_CREATE_MODE,
    SERVICE_CREATE_PROFILE_ONE,
    SERVICE_CREATE_PROFILE_SEVEN,
    SERVICE_CREATE_PROFILE_TWO,
    SERVICE_CREATE_TIMER_PROFILE_ONE,
    SERVICE_CREATE_TIMER_PROFILE_SEVEN,
    SERVICE_CREATE_TIMER_PROFILE_TWO,
    SERVICE_DELETE_PROFILE,
    SERVICE_GET_PROFILE_DEFINITIONS,
    SERVICE_RENAME_PROFILE,
    GlobalSystemType,
)
from .coordinator import HeatmiserNeoCoordinator
from .entity import (
    HeatmiserNeoEntity,
    HeatmiserNeoEntityDescription,
    HeatmiserNeoHubEntity,
    HeatmiserNeoHubEntityDescription,
    call_custom_action,
    profile_sensor_enabled_by_default,
)
from .helpers import get_profile_definition, profile_level

_LOGGER = logging.getLogger(__name__)

HOLIDAY_FORMAT = "%a %b %d %H:%M:%S %Y\n"

HEATING_LEVELS_4 = {0: "wake", 1: "leave", 2: "return", 3: "sleep"}

HEATING_LEVELS_6 = {
    0: "wake",
    1: "level1",
    2: "level2",
    3: "level3",
    4: "level4",
    5: "sleep",
}

TIMER_LEVELS_4 = {0: "time1", 1: "time2", 2: "time3", 3: "time4"}

SCHEDULE_WEEKDAYS = {
    ScheduleFormat.ONE: ["sunday"],
    ScheduleFormat.TWO: ["sunday", "monday"],
    ScheduleFormat.SEVEN: [
        "sunday",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
    ],
}


def time_str(value: Any) -> str:
    """Input validator for time string in profile services."""
    try:
        time_val = dt_util.parse_time(value)
    except TypeError as err:
        raise vol.Invalid("Not a parseable type") from err

    if time_val is None:
        raise vol.Invalid(f"Invalid time specified: {value}")

    return time_val.strftime("%H:%M")


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

    neo_devices, _ = coordinator.data
    system_data = coordinator.system_data

    _LOGGER.info("Adding Neo Sensors")

    async_add_entities(
        HeatmiserNeoHubSensor(coordinator, hub, description, entry)
        for description in HUB_SENSORS
        if description.setup_filter_fn(coordinator)
    )

    async_add_entities(
        HeatmiserNeoSensor(neodevice, coordinator, hub, description, entry)
        for description in SENSORS
        for neodevice in neo_devices.values()
        if description.setup_filter_fn(neodevice, system_data)
    )

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_RENAME_PROFILE,
        {
            vol.Required(ATTR_NAME_OLD): cv.string,
            vol.Required(ATTR_NAME_NEW): cv.string,
        },
        call_custom_action,
    )
    platform.async_register_entity_service(
        SERVICE_DELETE_PROFILE,
        {vol.Required(ATTR_NAME): cv.string},
        call_custom_action,
    )
    platform.async_register_entity_service(
        SERVICE_CREATE_PROFILE_ONE,
        {
            vol.Required(ATTR_NAME): cv.string,
            vol.Optional(ATTR_CREATE_MODE, default=OPTION_CREATE_MODE_CREATE): vol.In(
                OPTIONS_CREATE_MODE
            ),
            vol.Required(ATTR_SUNDAY_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_SUNDAY_TEMPERATURES): vol.All(
                cv.ensure_list, [vol.Coerce(float)]
            ),
        },
        call_custom_action,
    )
    platform.async_register_entity_service(
        SERVICE_CREATE_PROFILE_TWO,
        {
            vol.Required(ATTR_NAME): cv.string,
            vol.Optional(ATTR_CREATE_MODE, default=OPTION_CREATE_MODE_CREATE): vol.In(
                OPTIONS_CREATE_MODE
            ),
            vol.Required(ATTR_MONDAY_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_MONDAY_TEMPERATURES): vol.All(
                cv.ensure_list, [vol.Coerce(float)]
            ),
            vol.Required(ATTR_SUNDAY_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_SUNDAY_TEMPERATURES): vol.All(
                cv.ensure_list, [vol.Coerce(float)]
            ),
        },
        call_custom_action,
    )
    platform.async_register_entity_service(
        SERVICE_CREATE_PROFILE_SEVEN,
        {
            vol.Required(ATTR_NAME): cv.string,
            vol.Optional(ATTR_CREATE_MODE, default=OPTION_CREATE_MODE_CREATE): vol.In(
                OPTIONS_CREATE_MODE
            ),
            vol.Required(ATTR_MONDAY_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_MONDAY_TEMPERATURES): vol.All(
                cv.ensure_list, [vol.Coerce(float)]
            ),
            vol.Required(ATTR_TUESDAY_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_TUESDAY_TEMPERATURES): vol.All(
                cv.ensure_list, [vol.Coerce(float)]
            ),
            vol.Required(ATTR_WEDNESDAY_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_WEDNESDAY_TEMPERATURES): vol.All(
                cv.ensure_list, [vol.Coerce(float)]
            ),
            vol.Required(ATTR_THURSDAY_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_THURSDAY_TEMPERATURES): vol.All(
                cv.ensure_list, [vol.Coerce(float)]
            ),
            vol.Required(ATTR_FRIDAY_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_FRIDAY_TEMPERATURES): vol.All(
                cv.ensure_list, [vol.Coerce(float)]
            ),
            vol.Required(ATTR_SATURDAY_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_SATURDAY_TEMPERATURES): vol.All(
                cv.ensure_list, [vol.Coerce(float)]
            ),
            vol.Required(ATTR_SUNDAY_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_SUNDAY_TEMPERATURES): vol.All(
                cv.ensure_list, [vol.Coerce(float)]
            ),
        },
        call_custom_action,
    )
    platform.async_register_entity_service(
        SERVICE_CREATE_TIMER_PROFILE_ONE,
        {
            vol.Required(ATTR_NAME): cv.string,
            vol.Optional(ATTR_CREATE_MODE, default=OPTION_CREATE_MODE_CREATE): vol.In(
                OPTIONS_CREATE_MODE
            ),
            vol.Required(ATTR_SUNDAY_ON_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_SUNDAY_OFF_TIMES): vol.All(cv.ensure_list, [time_str]),
        },
        call_custom_action,
    )
    platform.async_register_entity_service(
        SERVICE_CREATE_TIMER_PROFILE_TWO,
        {
            vol.Required(ATTR_NAME): cv.string,
            vol.Optional(ATTR_CREATE_MODE, default=OPTION_CREATE_MODE_CREATE): vol.In(
                OPTIONS_CREATE_MODE
            ),
            vol.Required(ATTR_MONDAY_ON_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_MONDAY_OFF_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_SUNDAY_ON_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_SUNDAY_OFF_TIMES): vol.All(cv.ensure_list, [time_str]),
        },
        call_custom_action,
    )
    platform.async_register_entity_service(
        SERVICE_CREATE_TIMER_PROFILE_SEVEN,
        {
            vol.Required(ATTR_NAME): cv.string,
            vol.Optional(ATTR_CREATE_MODE, default=OPTION_CREATE_MODE_CREATE): vol.In(
                OPTIONS_CREATE_MODE
            ),
            vol.Required(ATTR_MONDAY_ON_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_MONDAY_OFF_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_TUESDAY_ON_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_TUESDAY_OFF_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_WEDNESDAY_ON_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_WEDNESDAY_OFF_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_THURSDAY_ON_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_THURSDAY_OFF_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_FRIDAY_ON_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_FRIDAY_OFF_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_SATURDAY_ON_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_SATURDAY_OFF_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_SUNDAY_ON_TIMES): vol.All(cv.ensure_list, [time_str]),
            vol.Required(ATTR_SUNDAY_OFF_TIMES): vol.All(cv.ensure_list, [time_str]),
        },
        call_custom_action,
    )
    platform.async_register_entity_service(
        SERVICE_GET_PROFILE_DEFINITIONS,
        {
            vol.Optional(ATTR_FRIENDLY_MODE, default=False): cv.boolean,
        },
        call_custom_action,
        supports_response=SupportsResponse.ONLY,
    )


async def async_rename_profile(
    entity: HeatmiserNeoHubEntity, service_call: ServiceCall
):
    """Rename a profile."""
    coordinator = entity.coordinator
    old_name = service_call.data[ATTR_NAME_OLD]
    new_name = service_call.data[ATTR_NAME_NEW]
    profile_id, timer = _check_profile_name(old_name, coordinator)
    conflicting_profile_id, _ = _check_profile_name(new_name, coordinator)
    if not profile_id:
        raise HomeAssistantError(f"Old name '{old_name}' does not exist")
    if conflicting_profile_id:
        raise HomeAssistantError(f"New name '{new_name}' already in use")

    await entity.coordinator.hub.rename_profile(old_name, new_name)
    if timer:
        entity.coordinator.timer_profiles[profile_id].name = new_name
    else:
        entity.coordinator.profiles[profile_id].name = new_name


async def async_delete_profile(
    entity: HeatmiserNeoHubEntity, service_call: ServiceCall
):
    """Rename a profile."""
    coordinator = entity.coordinator
    profile_name = service_call.data[ATTR_NAME]
    profile_id, timer = _check_profile_name(profile_name, coordinator)
    if not profile_id:
        raise HomeAssistantError(f"Profile '{profile_name}' does not exist")

    await entity.coordinator.hub.delete_profile(profile_name)
    if timer:
        del entity.coordinator.timer_profiles[profile_id]
    else:
        del entity.coordinator.profiles[profile_id]


async def async_get_profile_definitions(
    entity: HeatmiserNeoHubEntity, service_call: ServiceCall
):
    """Get definitions of all profiles."""
    friendly_mode = service_call.data.get(ATTR_FRIENDLY_MODE, False)

    heating = {
        p.name: get_profile_definition(k, entity.coordinator, friendly_mode)
        for k, p in entity.coordinator.profiles.items()
    }
    timers = {
        p.name: get_profile_definition(k, entity.coordinator, friendly_mode)
        for k, p in entity.coordinator.timer_profiles.items()
    }

    return {"heating_profiles": heating, "timer_profiles": timers}


async def async_create_profile(
    entity: HeatmiserNeoEntity,
    service_call: ServiceCall,
    requested_format: ScheduleFormat,
    timer: bool = False,
):
    """Create or update a profile."""
    _LOGGER.debug("Create profile - service_call=%s", service_call)
    coordinator = entity.coordinator
    profile_format = coordinator.system_data.FORMAT
    if timer and profile_format is ScheduleFormat.ZERO:
        profile_format = coordinator.system_data.ALT_TIMER_FORMAT

    if profile_format is ScheduleFormat.ZERO:
        raise HomeAssistantError(
            "Hub is in non programmable mode. Can't create profiles"
        )

    if requested_format is not profile_format:
        raise HomeAssistantError(
            f"Requested profile format ({requested_format}) does not match hub format ({profile_format})"
        )

    create_mode = service_call.data.get(ATTR_CREATE_MODE, OPTION_CREATE_MODE_CREATE)
    profile_name = service_call.data[ATTR_NAME]
    profile_id, timer_profile = _check_profile_name(profile_name, coordinator)

    if not profile_id:
        if create_mode == OPTION_CREATE_MODE_UPDATE:
            raise HomeAssistantError(
                f"Could not find existing profile with name '{profile_name}'"
            )
    else:
        if create_mode == OPTION_CREATE_MODE_CREATE:
            raise HomeAssistantError(
                f"A profile with name '{profile_name}' already exists"
            )
        if timer != timer_profile:
            raise HomeAssistantError(
                f"A {'heating' if timer else 'timer'} profile with name '{profile_name}' already exists"
            )

    heating_levels = 4 if timer else coordinator.system_data.HEATING_LEVELS

    weekdays = SCHEDULE_WEEKDAYS[profile_format]
    weekday_levels = {
        wd: _convert_to_profile_info(service_call, wd, heating_levels, timer)
        for wd in weekdays
    }

    msg_details = {}
    if profile_id:
        msg_details["ID"] = profile_id
    msg_details["info"] = weekday_levels
    msg_details["name"] = profile_name

    msg = {"STORE_PROFILE": msg_details}
    reply = {"result": "profile created"}

    _LOGGER.debug("Create profile - msg=%s", json.dumps(msg))
    await entity.coordinator.hub._send(msg, reply)  # noqa: SLF001

    await coordinator.async_request_refresh()


def _convert_to_profile_info(
    service_call: ServiceCall, weekday: str, levels: int = 4, timer: bool = False
) -> dict:
    list1 = None
    list2 = None
    empty1 = "24:00"
    empty2 = None
    if timer:
        on_key = weekday + "_on_times"
        off_key = weekday + "_off_times"
        list1 = service_call.data.get(on_key, [])
        list2 = service_call.data.get(off_key, [])
        empty2 = empty1

        if len(list1) != len(list2):
            raise HomeAssistantError(
                f"On Times and Off Times lists for {weekday} must have same length"
            )
    else:
        times_key = weekday + "_times"
        temperatures_key = weekday + "_temperatures"

        list1 = service_call.data.get(times_key, [])
        list2 = service_call.data.get(temperatures_key, [])
        empty2 = 5

        if len(list1) != len(list2):
            raise HomeAssistantError(
                f"Times and Temperatures lists for {weekday} must have same length"
            )

    if len(list1) > levels:
        raise HomeAssistantError(
            f"Too many levels defined for {weekday}. Hub only supports {levels} levels"
        )

    tuples = sorted([(list1[i], list2[i]) for i in range(len(list1))])

    return {
        _convert_level_index(timer, levels, i): [tuples[i][0], tuples[i][1]]
        if i < len(tuples)
        else [empty1, empty2]
        for i in range(levels)
    }


def _convert_level_index(timer: bool, configured_levels: int, level_idx: int) -> str:
    if timer:
        return TIMER_LEVELS_4[level_idx]
    if configured_levels == 4:
        return HEATING_LEVELS_4[level_idx]
    return HEATING_LEVELS_6[level_idx]


def _check_profile_name(profile_name: str, coordinator: HeatmiserNeoCoordinator):
    ids = [
        k
        for k, p in coordinator.timer_profiles.items()
        if p.name.casefold() == profile_name.casefold()
    ]
    if len(ids) == 1:
        return ids[0], True

    ids = [
        k
        for k, p in coordinator.profiles.items()
        if p.name.casefold() == profile_name.casefold()
    ]

    return ids[0] if len(ids) == 1 else None, False


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
        custom_functions={
            SERVICE_RENAME_PROFILE: async_rename_profile,
            SERVICE_DELETE_PROFILE: async_delete_profile,
            SERVICE_GET_PROFILE_DEFINITIONS: async_get_profile_definitions,
            SERVICE_CREATE_PROFILE_ONE: lambda e, s: async_create_profile(
                e, s, ScheduleFormat.ONE
            ),
            SERVICE_CREATE_PROFILE_TWO: lambda e, s: async_create_profile(
                e, s, ScheduleFormat.TWO
            ),
            SERVICE_CREATE_PROFILE_SEVEN: lambda e, s: async_create_profile(
                e, s, ScheduleFormat.SEVEN
            ),
            SERVICE_CREATE_TIMER_PROFILE_ONE: lambda e, s: async_create_profile(
                e, s, ScheduleFormat.ONE, True
            ),
            SERVICE_CREATE_TIMER_PROFILE_TWO: lambda e, s: async_create_profile(
                e, s, ScheduleFormat.TWO, True
            ),
            SERVICE_CREATE_TIMER_PROFILE_SEVEN: lambda e, s: async_create_profile(
                e, s, ScheduleFormat.SEVEN, True
            ),
        },
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
        options=[4, 6],
        value_fn=lambda coordinator: coordinator.system_data.HEATING_LEVELS,
        translation_key="hub_profile_heating_levels",
    ),
)


class HeatmiserNeoSensor(HeatmiserNeoEntity, SensorEntity):
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


class HeatmiserNeoHubSensor(HeatmiserNeoHubEntity, SensorEntity):
    """Heatmiser Neo button entity."""

    def __init__(
        self,
        coordinator: HeatmiserNeoCoordinator,
        hub: NeoHub,
        entity_description: HeatmiserNeoSensorEntityDescription,
        config_entry: HeatmiserNeoConfigEntry,
    ) -> None:
        """Initialize Heatmiser Neo button entity."""
        super().__init__(coordinator, hub, entity_description, config_entry)

    @property
    def native_value(self):
        """Return the sensors temperature value."""
        return self.entity_description.value_fn(self.coordinator)


def _profile_current_temp(profile_id, entity: HeatmiserNeoSensor) -> float | None:
    """Convert a profile id to current temperature."""
    level = profile_level(profile_id, entity.data, entity.coordinator)
    if level:
        return float(level[1])
    return None


def _profile_next_temp(profile_id, entity: HeatmiserNeoSensor) -> float | None:
    _, temp = _profile_next_level(profile_id, entity)
    if temp:
        return float(temp)
    return None


def _profile_next_time(profile_id, entity: HeatmiserNeoSensor) -> str | None:
    t, _ = _profile_next_level(profile_id, entity)
    if not t:
        return None
    device_time = entity.data._data_.TIME
    if len(device_time) == 4:
        device_time = f"0{device_time}"
    profile_time = datetime.datetime.strptime(t, "%H:%M")
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
    if t < device_time:
        return profile_datetime + datetime.timedelta(days=1)
    return profile_datetime


def _profile_next_level(profile_id, entity: HeatmiserNeoSensor):
    """Convert a profile id to next level."""
    lv = profile_level(profile_id, entity.data, entity.coordinator, True)
    if lv:
        return lv[0], lv[1]
    return None, None


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
