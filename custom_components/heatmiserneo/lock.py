# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""Heatmiser Neo Binary Sensors via Heatmiser Neo-hub."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
import re
from typing import Any

from neohubapi.neohub import NeoHub, NeoStat

from homeassistant.components.lock import (
    DOMAIN as LOCK_DOMAIN,
    LockEntity,
    LockEntityDescription,
)
from homeassistant.const import ATTR_CODE, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import HEATMISER_TYPE_IDS_LOCK
from .coordinator import HeatmiserNeoConfigEntry, HeatmiserNeoCoordinator
from .entity import (
    HeatmiserNeoEntity,
    HeatmiserNeoEntityDescription,
    async_setup_entities,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatmiserNeoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Heatmiser Neo Switch entities."""
    hub = entry.runtime_data.hub
    coordinator = entry.runtime_data.coordinator

    if coordinator.data is None:
        _LOGGER.error("Coordinator data is None. Cannot set up lock entities")
        return

    @callback
    def device_entities(new_devices: list[NeoStat]):
        return [
            HeatmiserNeoLockEntity(neodevice, coordinator, hub, description, entry)
            for description in LOCKS
            for neodevice in new_devices
            if description.setup_filter_fn(neodevice, coordinator.system_data)
        ]

    await async_setup_entities(
        hass, entry, async_add_entities, Platform.LOCK, None, device_entities
    )


# Ideally we would set this on the lock entity itself
# but doing so adds a code entry dialog to the UI
# which we don't want
pin_format = r"^\d{1,4}$"
pin_format_cmp = re.compile(pin_format)


async def _async_lock_device(entity: HeatmiserNeoEntity, **kwargs):
    """Lock a thermostat."""
    code = str(kwargs.get(ATTR_CODE, 0))
    if not pin_format_cmp.match(code):
        raise ServiceValidationError(
            translation_domain=LOCK_DOMAIN,
            translation_key="add_default_code",
            translation_placeholders={
                "entity_id": entity.entity_id,
                "code_format": pin_format,
            },
        )
    await entity.data.set_lock(int(code))


async def _async_unlock_device(entity: HeatmiserNeoEntity):
    """Unlock a thermostat."""
    await entity.data.unlock()


@dataclass(frozen=True, kw_only=True)
class HeatmiserNeoLockEntityDescription(
    HeatmiserNeoEntityDescription, LockEntityDescription
):
    """Describes a button entity."""

    value_fn: Callable[[HeatmiserNeoEntity], bool]
    default_pin_fn: Callable[[HeatmiserNeoEntity], int]
    lock_fn: Callable[[HeatmiserNeoEntity, Any], Awaitable[None]]
    unlock_fn: Callable[[HeatmiserNeoEntity], Awaitable[None]]


LOCKS: tuple[HeatmiserNeoLockEntityDescription, ...] = (
    HeatmiserNeoLockEntityDescription(
        key="heatmiser_neo_stat_lock",
        translation_key="lock",
        value_fn=lambda entity: entity.data.lock,
        default_pin_fn=lambda entity: entity.data.pin_number,
        lock_fn=_async_lock_device,
        unlock_fn=_async_unlock_device,
        setup_filter_fn=lambda device, _: device.device_type in HEATMISER_TYPE_IDS_LOCK,
    ),
)


class HeatmiserNeoLockEntity(
    HeatmiserNeoEntity[HeatmiserNeoLockEntityDescription], LockEntity
):
    """Heatmiser Neo switch entity."""

    def __init__(
        self,
        neostat: NeoStat,
        coordinator: HeatmiserNeoCoordinator,
        hub: NeoHub,
        entity_description: HeatmiserNeoLockEntityDescription,
        config_entry: HeatmiserNeoConfigEntry,
    ) -> None:
        """Initialize Heatmiser Neo lock entity."""
        super().__init__(
            neostat,
            coordinator,
            hub,
            entity_description,
            config_entry,
        )
        self._update()

    async def async_lock(self, **kwargs):
        """Turn the entity on."""
        await self.entity_description.lock_fn(self, **kwargs)
        self.data.lock = True
        self.coordinator.async_update_listeners()

    async def async_unlock(self, **kwargs):
        """Turn the entity off."""
        await self.entity_description.unlock_fn(self)
        self.data.lock = False
        self.coordinator.async_update_listeners()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update()
        super()._handle_coordinator_update()

    def _update(self):
        if self.entity_description.default_pin_fn:
            self._lock_option_default_code = self.entity_description.default_pin_fn(
                self
            )
        self._attr_is_locked = self.entity_description.value_fn(self)
