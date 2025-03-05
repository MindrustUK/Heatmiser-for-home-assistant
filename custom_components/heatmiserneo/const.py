# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
"""Constants used by multiple Heatmiser Neo modules."""

from datetime import timedelta
import enum

from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
    UnitOfTemperature,
)

DOMAIN = "heatmiserneo"

DEFAULT_HOST = "Neo-Hub"
DEFAULT_PORT = 4242
DEFAULT_WEBSOCKET_PORT = 4243

DEFAULT_TIMER_HOLD_DURATION = 30
DEFAULT_NEOSTAT_HOLD_DURATION = 30
DEFAULT_NEOSTAT_TEMPERATURE_BOOST = 2

DISCOVER_SCAN_TIMEOUT = 3
DISCOVERY_INTERVAL = timedelta(minutes=15)
DISCOVER_AUTO_CONNECT_TIMEOUT = 120

CONF_CONN_METHOD_WEBSOCKET = "conn_method_websocket"
CONF_CONN_METHOD_LEGACY = "conn_method_legacy"


CONF_DISCOVERY_METHOD_AUTO_CONNECT = "discovery_method_auto_connect"
CONF_DISCOVERY_METHOD_HUBSEEK = "discovery_method_hubseek"
CONF_DISCOVERY_METHOD_MANUAL = "discovery_method_manual"


CONF_DEFAULTS = "defaults"
CONF_HVAC_MODES = "hvac_modes"
CONF_TIMER_OPTIONS = "timer_options"
CONF_THERMOSTAT_OPTIONS = "thermostat_options"
CONF_STAT_HOLD_DURATION = "stat_hold_duration"
CONF_STAT_HOLD_TEMP = "stat_hold_temp"
CONF_TIMER_HOLD_DURATION = "timer_hold_duration"

SERVICE_HOLD_ON = "hold_on"
SERVICE_HOLD_OFF = "hold_off"
SERVICE_TIMER_HOLD_ON = "timer_hold_on"
SERVICE_GET_DEVICE_PROFILE_DEFINITION = "get_device_profile_definition"
SERVICE_GET_PROFILE_DEFINITIONS = "get_profile_definitions"
SERVICE_CREATE_PROFILE_ONE = "create_profile_one"
SERVICE_CREATE_PROFILE_TWO = "create_profile_two"
SERVICE_CREATE_PROFILE_SEVEN = "create_profile_seven"
SERVICE_CREATE_TIMER_PROFILE_ONE = "create_timer_profile_one"
SERVICE_CREATE_TIMER_PROFILE_TWO = "create_timer_profile_two"
SERVICE_CREATE_TIMER_PROFILE_SEVEN = "create_timer_profile_seven"
SERVICE_RENAME_PROFILE = "rename_profile"
SERVICE_DELETE_PROFILE = "delete_profile"
SERVICE_HUB_AWAY = "set_away_mode"
ATTR_HOLD_DURATION = "hold_duration"
ATTR_HOLD_STATE = "hold_state"
ATTR_HOLD_TEMPERATURE = "hold_temperature"
ATTR_AWAY_STATE = "away"
# ATTR_AWAY_START = "start"
ATTR_AWAY_END = "end"
ATTR_NAME_OLD = "old_name"
ATTR_NAME_NEW = "new_name"
ATTR_FRIENDLY_MODE = "friendly_mode"
ATTR_CREATE_MODE = "mode"
ATTR_MONDAY_TIMES = "monday_times"
ATTR_MONDAY_TEMPERATURES = "monday_temperatures"
ATTR_TUESDAY_TIMES = "tuesday_times"
ATTR_TUESDAY_TEMPERATURES = "tuesday_temperatures"
ATTR_WEDNESDAY_TIMES = "wednesday_times"
ATTR_WEDNESDAY_TEMPERATURES = "wednesday_temperatures"
ATTR_THURSDAY_TIMES = "thursday_times"
ATTR_THURSDAY_TEMPERATURES = "thursday_temperatures"
ATTR_FRIDAY_TIMES = "friday_times"
ATTR_FRIDAY_TEMPERATURES = "friday_temperatures"
ATTR_SATURDAY_TIMES = "saturday_times"
ATTR_SATURDAY_TEMPERATURES = "saturday_temperatures"
ATTR_SUNDAY_TIMES = "sunday_times"
ATTR_SUNDAY_TEMPERATURES = "sunday_temperatures"
ATTR_MONDAY_ON_TIMES = "monday_on_times"
ATTR_MONDAY_OFF_TIMES = "monday_off_times"
ATTR_TUESDAY_ON_TIMES = "tuesday_on_times"
ATTR_TUESDAY_OFF_TIMES = "tuesday_off_times"
ATTR_WEDNESDAY_ON_TIMES = "wednesday_on_times"
ATTR_WEDNESDAY_OFF_TIMES = "wednesday_off_times"
ATTR_THURSDAY_ON_TIMES = "thursday_on_times"
ATTR_THURSDAY_OFF_TIMES = "thursday_off_times"
ATTR_FRIDAY_ON_TIMES = "friday_on_times"
ATTR_FRIDAY_OFF_TIMES = "friday_off_times"
ATTR_SATURDAY_ON_TIMES = "saturday_on_times"
ATTR_SATURDAY_OFF_TIMES = "saturday_off_times"
ATTR_SUNDAY_ON_TIMES = "sunday_on_times"
ATTR_SUNDAY_OFF_TIMES = "sunday_off_times"

OPTION_CREATE_MODE_CREATE = "create"
OPTION_CREATE_MODE_UPDATE = "update"
OPTION_CREATE_MODE_UPSERT = "upsert"

OPTIONS_CREATE_MODE = [
    OPTION_CREATE_MODE_CREATE,
    OPTION_CREATE_MODE_UPDATE,
    OPTION_CREATE_MODE_UPSERT,
]

PRESET_STANDBY = "standby"

PROFILE_0 = "PROFILE_0"

HEATMISER_HUB_PRODUCT_LIST = [
    "NULL",
    "NeoHub Version 1",
    "NeoHub Version 2",
    "NeoHub Mini",
]

HEATMISER_PRODUCT_LIST = [
    "NULL",
    "NeoStat V1",
    "SmartStat",
    "CoolSwitch",
    "TCM RH",
    "Contact Sensor",
    "Neo Plug",
    "NeoAir",
    "SmartStat HC",
    "NeoAir HW",
    "Repeater",
    "NeoStat HC",
    "NeoStat V2",
    "NeoAir V2",
    "Air Sensor",
    "NeoAir V2 Combo",
    "RF Switch Wifi",
    "Edge WiFi",
]

HEATMISER_TYPE_IDS_THERMOSTAT = {1, 2, 7, 8, 9, 11, 12, 13, 15, 17}
HEATMISER_TYPE_IDS_TIMER = {1, 2, 6, 7, 8, 9, 11, 12, 13, 15, 17}
HEATMISER_TYPE_IDS_PLUG = {6}
HEATMISER_TYPE_IDS_HC = {8, 11}
HEATMISER_TYPE_IDS_REPEATER = {10}
HEATMISER_TYPE_IDS_THERMOSTAT_NOT_HC = HEATMISER_TYPE_IDS_THERMOSTAT.difference(
    HEATMISER_TYPE_IDS_HC
)
HEATMISER_TYPE_IDS_AWAY = HEATMISER_TYPE_IDS_THERMOSTAT.union(HEATMISER_TYPE_IDS_TIMER)
HEATMISER_TYPE_IDS_STANDBY = HEATMISER_TYPE_IDS_AWAY.difference(HEATMISER_TYPE_IDS_PLUG)
HEATMISER_TYPE_IDS_HOLD = HEATMISER_TYPE_IDS_THERMOSTAT.union(HEATMISER_TYPE_IDS_TIMER)
HEATMISER_TYPE_IDS_IDENTIFY = HEATMISER_TYPE_IDS_THERMOSTAT.union(
    HEATMISER_TYPE_IDS_TIMER
).difference(HEATMISER_TYPE_IDS_PLUG)
HEATMISER_TYPE_IDS_LOCK = HEATMISER_TYPE_IDS_IDENTIFY


# This should be in the neohubapi.neohub enums code
class AvailableMode(str, enum.Enum):
    """Operating mode options for NeoStats."""

    HEAT = "heat"
    COOL = "cool"
    VENT = "vent"
    AUTO = "auto"


class GlobalSystemType(str, enum.Enum):
    """Global System Types for NeoStat HC."""

    HEAT_ONLY = "HeatOnly"
    COOL_ONLY = "CoolOnly"
    HEAT_COOL = "HeatOrCool"
    INDEPENDENT = "Independent"


class ModeSelectOption(str, enum.Enum):
    """Operating mode options for NeoPlugs and NeoStats in timer mode."""

    AUTO = "auto"
    OVERRIDE_OFF = "override_off"
    OVERRIDE_ON = "override_on"
    STANDBY = "standby"
    MANUAL_ON = "on"
    MANUAL_OFF = "off"
    AWAY = "away"


HEATMISER_TEMPERATURE_UNIT_HA_UNIT = {
    "F": UnitOfTemperature.FAHRENHEIT,
    "C": UnitOfTemperature.CELSIUS,
}

HEATMISER_FAN_SPEED_HA_FAN_MODE = {
    "High": FAN_HIGH,
    "Medium": FAN_MEDIUM,
    "Low": FAN_LOW,
    "Auto": FAN_AUTO,
    "Off": FAN_OFF,
}


class FanControl(str, enum.Enum):
    """Fan control mode options for NeoStat HC."""

    MANUAL = "Manual"
    AUTOMATIC = "Automatic"
