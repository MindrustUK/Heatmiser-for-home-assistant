"""Services for HeatmiserNeo."""

from __future__ import annotations

from collections.abc import Callable
import datetime
from functools import partial
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_CONFIG_ENTRY_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import ConfigEntrySelector

from .const import ATTR_AWAY_END, ATTR_AWAY_STATE, DOMAIN, SERVICE_HUB_AWAY
from .coordinator import HeatmiserNeoConfigEntry
from .helpers import device_supports_away, set_away, set_holiday

# SERVICE_SETTINGS = "change_setting"
# SERVICE_CAPTURE_IMAGE = "capture_image"
# SERVICE_TRIGGER_AUTOMATION = "trigger_automation"

# SERVICE_SET_AWAY = ""

# ATTR_SETTING = "setting"
# ATTR_VALUE = "value"


# CHANGE_SETTING_SCHEMA = vol.Schema(
#     {vol.Required(ATTR_SETTING): cv.string, vol.Required(ATTR_VALUE): cv.string}
# )

# CAPTURE_IMAGE_SCHEMA = vol.Schema({ATTR_ENTITY_ID: cv.entity_ids})

# AUTOMATION_SCHEMA = vol.Schema({ATTR_ENTITY_ID: cv.entity_ids})


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


SET_AWAY_MODE_SCHEMA = vol.All(
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


async def _async_set_away_mode(call: ServiceCall) -> None:
    """Set away mode on the hub."""
    config_entry: HeatmiserNeoConfigEntry | None
    state = call.data[ATTR_AWAY_STATE]
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

    coordinator = config_entry.runtime_data.coordinator
    hub = config_entry.runtime_data.coordinator.hub

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

            await coordinator.hub.set_holiday(
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


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Home Assistant services."""

    hass.services.async_register(
        DOMAIN, SERVICE_HUB_AWAY, _async_set_away_mode, schema=SET_AWAY_MODE_SCHEMA
    )
