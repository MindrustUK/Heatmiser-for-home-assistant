# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

import enum

"""Constants used by multiple Heatmiser Neo modules."""
DOMAIN = "heatmiserneo"

HUB = "Hub"
COORDINATOR = "Coordinator"

DEFAULT_HOST = "Neo-Hub"
DEFAULT_PORT = 4242
DEFAULT_TOKEN = ""

CONF_HVAC_MODES = "hvac_modes"

SERVICE_HOLD_ON = "hold_on"
SERVICE_HOLD_OFF = "hold_off"
SERVICE_TIMER_HOLD_ON = "timer_hold_on"
ATTR_HOLD_DURATION = "hold_duration"
ATTR_HOLD_TEMPERATURE = "hold_temperature"

HEATMISER_HUB_PRODUCT_LIST = ["NULL", "NeoHub Version 1", "NeoHub Version 2", "NeoHub Mini"]

HEATMISER_PRODUCT_LIST = ["NULL", "NeoStat V1", "SmartStat", "CoolSwitch", "TCM RH", "Contact Sensor", "Neo Plug",
                          "NeoAir", "SmartStat HC", "NeoAir HW", "Repeater", "NeoStat HC", "NeoStat V2", "NeoAir V2",
                          "Air Sensor", "NeoAir V2 Combo", "RF Switch Wifi", "Edge WiFi"]

# This should be in the neohubapi.neohub enums code
class AvailableMode(str, enum.Enum):
    HEAT = "heat"
    COOL = "cool"
    VENT = "vent"
    AUTO = "auto"
