# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

import enum

"""Constants used by multiple Heatmiser Neo modules."""
DOMAIN = "heatmiserneo"

HUB = "Hub"
COORDINATOR = "Coordinator"

DEFAULT_HOST = "Neo-Hub"
DEFAULT_PORT = 4242

CONF_HVAC_MODES = "hvac_modes"

SERVICE_HOLD_ON = "hold_on"
SERVICE_HOLD_OFF = "hold_off"
ATTR_HOLD_DURATION = "hold_duration"
ATTR_HOLD_TEMPERATURE = "hold_temperature"

# This should be in the neohubapi.neohub enums code
class AvailableMode(str, enum.Enum):
    HEAT = "heat"
    COOL = "cool"
    VENT = "vent"
    AUTO = "auto"
