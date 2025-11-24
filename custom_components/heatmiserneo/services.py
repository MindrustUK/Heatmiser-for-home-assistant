"""Services for HeatmiserNeo."""

from __future__ import annotations

from collections.abc import Callable
import datetime
from functools import partial
import json
import logging
from typing import Any

from neohubapi.neohub import ScheduleFormat
import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_CONFIG_ENTRY_ID, ATTR_NAME
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import ConfigEntrySelector
import homeassistant.util.dt as dt_util

from .const import (
    ATTR_AWAY_END,
    ATTR_AWAY_STATE,
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
    DOMAIN,
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
    SERVICE_HUB_AWAY,
    SERVICE_RENAME_PROFILE,
)
from .coordinator import HeatmiserNeoConfigEntry
from .helpers import (
    check_profile_name,
    device_supports_away,
    get_profile_definition,
    set_away,
    set_holiday,
)

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


def _dates_only_provided_when_setting_away(
    state_key, end_key
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def validate(obj: dict[str, Any]) -> dict[str, Any]:
        """Test that end date is only provided when setting away."""
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


def time_str(value: Any) -> str:
    """Input validator for time string in profile services."""
    try:
        time_val = dt_util.parse_time(value)
    except TypeError as err:
        raise vol.Invalid("Not a parseable type") from err

    if time_val is None:
        raise vol.Invalid(f"Invalid time specified: {value}")

    return time_val.strftime("%H:%M")


SCHEMA_SET_AWAY_MODE = vol.All(
    vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): ConfigEntrySelector(
                {"integration": DOMAIN}
            ),
            vol.Required(ATTR_AWAY_STATE, default=False): cv.boolean,
            # vol.Optional(ATTR_AWAY_START): cv.datetime,
            vol.Optional(ATTR_AWAY_END): cv.datetime,
        }
    ),
    _dates_only_provided_when_setting_away(ATTR_AWAY_STATE, ATTR_AWAY_END),
)

SCHEMA_RENAME_PROFILE = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): ConfigEntrySelector(
            {"integration": DOMAIN}
        ),
        vol.Required(ATTR_NAME_OLD): cv.string,
        vol.Required(ATTR_NAME_NEW): cv.string,
    }
)

SCHEMA_DELETE_PROFILE = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): ConfigEntrySelector(
            {"integration": DOMAIN}
        ),
        vol.Required(ATTR_NAME): cv.string,
    }
)

SCHEMA_GET_PROFILE_DEFINITIONS = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): ConfigEntrySelector(
            {"integration": DOMAIN}
        ),
        vol.Optional(ATTR_FRIENDLY_MODE, default=False): cv.boolean,
    }
)

SCHEMA_CREATE_PROFILE_ONE = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): ConfigEntrySelector(
            {"integration": DOMAIN}
        ),
        vol.Required(ATTR_NAME): cv.string,
        vol.Optional(ATTR_CREATE_MODE, default=OPTION_CREATE_MODE_CREATE): vol.In(
            OPTIONS_CREATE_MODE
        ),
        vol.Required(ATTR_SUNDAY_TIMES): vol.All(cv.ensure_list, [time_str]),
        vol.Required(ATTR_SUNDAY_TEMPERATURES): vol.All(
            cv.ensure_list, [vol.Coerce(float)]
        ),
    }
)

SCHEMA_CREATE_PROFILE_TWO = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): ConfigEntrySelector(
            {"integration": DOMAIN}
        ),
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
    }
)

SCHEMA_CREATE_PROFILE_SEVEN = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): ConfigEntrySelector(
            {"integration": DOMAIN}
        ),
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
    }
)

SCHEMA_CREATE_TIMER_PROFILE_ONE = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): ConfigEntrySelector(
            {"integration": DOMAIN}
        ),
        vol.Required(ATTR_NAME): cv.string,
        vol.Optional(ATTR_CREATE_MODE, default=OPTION_CREATE_MODE_CREATE): vol.In(
            OPTIONS_CREATE_MODE
        ),
        vol.Required(ATTR_SUNDAY_ON_TIMES): vol.All(cv.ensure_list, [time_str]),
        vol.Required(ATTR_SUNDAY_OFF_TIMES): vol.All(cv.ensure_list, [time_str]),
    }
)

SCHEMA_CREATE_TIMER_PROFILE_TWO = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): ConfigEntrySelector(
            {"integration": DOMAIN}
        ),
        vol.Required(ATTR_NAME): cv.string,
        vol.Optional(ATTR_CREATE_MODE, default=OPTION_CREATE_MODE_CREATE): vol.In(
            OPTIONS_CREATE_MODE
        ),
        vol.Required(ATTR_MONDAY_ON_TIMES): vol.All(cv.ensure_list, [time_str]),
        vol.Required(ATTR_MONDAY_OFF_TIMES): vol.All(cv.ensure_list, [time_str]),
        vol.Required(ATTR_SUNDAY_ON_TIMES): vol.All(cv.ensure_list, [time_str]),
        vol.Required(ATTR_SUNDAY_OFF_TIMES): vol.All(cv.ensure_list, [time_str]),
    }
)

SCHEMA_CREATE_TIMER_PROFILE_SEVEN = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): ConfigEntrySelector(
            {"integration": DOMAIN}
        ),
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
    }
)


def _validate_config_entry(call: ServiceCall) -> HeatmiserNeoConfigEntry:
    config_entry: HeatmiserNeoConfigEntry | None
    entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
    if not (config_entry := call.hass.config_entries.async_get_entry(entry_id)):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="integration_not_found",
            translation_placeholders={"target": entry_id},
        )
    if config_entry.state is not ConfigEntryState.LOADED:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="not_loaded",
            translation_placeholders={"target": config_entry.title},
        )
    return config_entry


async def _async_set_away_mode(call: ServiceCall) -> None:
    """Set away mode on the hub."""
    config_entry: HeatmiserNeoConfigEntry = _validate_config_entry(call)
    state = call.data[ATTR_AWAY_STATE]

    coordinator = config_entry.runtime_data.coordinator
    hub = config_entry.runtime_data.hub

    holiday = None
    away = None
    if not state:
        if coordinator.live_data.HUB_AWAY:
            await hub.set_away(False)
            away = False
        if coordinator.live_data.HUB_HOLIDAY:
            await hub.cancel_holiday()
            holiday = False
    else:
        end_date: datetime.datetime | None = call.data.get(ATTR_AWAY_END)
        if end_date:
            if coordinator.live_data.HUB_AWAY:
                await hub.set_away(False)
                away = False

            await hub.set_holiday(
                datetime.datetime.now() - datetime.timedelta(days=1), end_date
            )
            holiday = True
        else:
            if coordinator.live_data.HUB_HOLIDAY:
                await hub.cancel_holiday()
                holiday = False
            await hub.set_away(True)
            away = True
    if away is not None:
        coordinator.update_in_memory_state(
            partial(set_away, away),
            device_supports_away,
        )
        coordinator.live_data.HUB_AWAY = away
    if holiday is not None:
        coordinator.update_in_memory_state(
            partial(set_holiday, holiday),
            device_supports_away,
        )
        coordinator.live_data.HUB_HOLIDAY = holiday


async def _async_rename_profile(call: ServiceCall) -> None:
    """Rename a profile."""
    config_entry: HeatmiserNeoConfigEntry = _validate_config_entry(call)

    coordinator = config_entry.runtime_data.coordinator
    hub = config_entry.runtime_data.hub

    old_name = call.data[ATTR_NAME_OLD]
    new_name = call.data[ATTR_NAME_NEW]
    profile_id, timer = check_profile_name(old_name, coordinator)
    conflicting_profile_id, _ = check_profile_name(new_name, coordinator)
    if not profile_id:
        raise HomeAssistantError(f"Old name '{old_name}' does not exist")
    if conflicting_profile_id:
        raise HomeAssistantError(f"New name '{new_name}' already in use")

    await hub.rename_profile(old_name, new_name)
    if timer:
        coordinator.timer_profiles[profile_id].name = new_name
    else:
        coordinator.profiles[profile_id].name = new_name


async def _async_delete_profile(call: ServiceCall) -> None:
    """Delete a profile."""
    config_entry: HeatmiserNeoConfigEntry = _validate_config_entry(call)

    coordinator = config_entry.runtime_data.coordinator
    hub = config_entry.runtime_data.hub

    profile_name = call.data[ATTR_NAME]
    profile_id, timer = check_profile_name(profile_name, coordinator)
    if not profile_id:
        raise HomeAssistantError(f"Profile '{profile_name}' does not exist")

    await hub.delete_profile(profile_name)
    if timer:
        del coordinator.timer_profiles[profile_id]
    else:
        del coordinator.profiles[profile_id]


async def _async_get_profile_definitions(call: ServiceCall) -> ServiceResponse:
    """Get definitions of all profiles."""
    config_entry: HeatmiserNeoConfigEntry = _validate_config_entry(call)

    coordinator = config_entry.runtime_data.coordinator

    friendly_mode = call.data.get(ATTR_FRIENDLY_MODE, False)

    heating = {
        str(p.name): get_profile_definition(k, coordinator, friendly_mode)
        for k, p in coordinator.profiles.items()
    }
    timers = {
        str(p.name): get_profile_definition(k, coordinator, friendly_mode)
        for k, p in coordinator.timer_profiles.items()
    }

    return {"heating_profiles": heating, "timer_profiles": timers}


async def _async_create_profile(
    requested_format: ScheduleFormat, timer: bool, call: ServiceCall
) -> None:
    config_entry: HeatmiserNeoConfigEntry = _validate_config_entry(call)

    coordinator = config_entry.runtime_data.coordinator
    hub = config_entry.runtime_data.hub
    _LOGGER.debug("Create profile - service_call=%s", call)

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

    create_mode = call.data.get(ATTR_CREATE_MODE, OPTION_CREATE_MODE_CREATE)
    profile_name = call.data[ATTR_NAME]
    profile_id, timer_profile = check_profile_name(profile_name, coordinator)

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
        wd: _convert_to_profile_info(call, wd, heating_levels, timer) for wd in weekdays
    }

    msg_details = {}
    if profile_id:
        msg_details["ID"] = profile_id
    msg_details["info"] = weekday_levels
    msg_details["name"] = profile_name

    msg = {"STORE_PROFILE": msg_details}
    reply = {"result": "profile created"}

    _LOGGER.debug("Create profile - msg=%s", json.dumps(msg))
    await hub._send(msg, reply)  # noqa: SLF001

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


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Home Assistant services."""

    hass.services.async_register(
        DOMAIN, SERVICE_HUB_AWAY, _async_set_away_mode, schema=SCHEMA_SET_AWAY_MODE
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RENAME_PROFILE,
        _async_rename_profile,
        schema=SCHEMA_RENAME_PROFILE,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_PROFILE,
        _async_delete_profile,
        schema=SCHEMA_DELETE_PROFILE,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PROFILE_DEFINITIONS,
        _async_get_profile_definitions,
        schema=SCHEMA_GET_PROFILE_DEFINITIONS,
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_PROFILE_ONE,
        partial(_async_create_profile, ScheduleFormat.ONE, False),
        schema=SCHEMA_CREATE_PROFILE_ONE,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_PROFILE_TWO,
        partial(_async_create_profile, ScheduleFormat.TWO, False),
        schema=SCHEMA_CREATE_PROFILE_TWO,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_PROFILE_SEVEN,
        partial(_async_create_profile, ScheduleFormat.SEVEN, False),
        schema=SCHEMA_CREATE_PROFILE_SEVEN,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_TIMER_PROFILE_ONE,
        partial(_async_create_profile, ScheduleFormat.ONE, True),
        schema=SCHEMA_CREATE_TIMER_PROFILE_ONE,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_TIMER_PROFILE_TWO,
        partial(_async_create_profile, ScheduleFormat.TWO, True),
        schema=SCHEMA_CREATE_TIMER_PROFILE_TWO,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_TIMER_PROFILE_SEVEN,
        partial(_async_create_profile, ScheduleFormat.SEVEN, True),
        schema=SCHEMA_CREATE_TIMER_PROFILE_SEVEN,
    )
