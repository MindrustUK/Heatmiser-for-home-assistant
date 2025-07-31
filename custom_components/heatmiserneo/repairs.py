"""Repairs flows for Home Connect."""

import logging

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant
import homeassistant.helpers.device_registry as dr

_LOGGER = logging.getLogger(__name__)


class CleanupOldDevicesFlow(RepairsFlow):
    """Handler for deleting old devices that shouldn't exist anymore."""

    def __init__(self, entry_id: str) -> None:
        """Initialize."""
        self._entry_id = entry_id

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of a fix flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the confirm step of a fix flow."""
        if user_input is not None:
            entry = self.hass.config_entries.async_get_entry(self._entry_id)

            device_registry = dr.async_get(self.hass)

            registry_devices = dr.async_entries_for_config_entry(
                device_registry, entry.entry_id
            )
            hub_device_id = next(
                iter({d.via_device_id for d in registry_devices if d.via_device_id})
            )
            non_hub_devices = [
                d
                for d in registry_devices
                if not d.via_device_id and d.id != hub_device_id
            ]
            for d in non_hub_devices:
                _LOGGER.debug("delete old device %s - %s", d.id, d.name)
                device_registry.async_remove_device(d.id)

            await self.hass.config_entries.async_reload(self._entry_id)

            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
        )


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, str] | None
) -> RepairsFlow:
    """Create flow."""

    entry_id = data["entry_id"]

    if issue_id.startswith("cleanup_old_devices"):
        return CleanupOldDevicesFlow(entry_id)

    return ConfirmRepairFlow()
