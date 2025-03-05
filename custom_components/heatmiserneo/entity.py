# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
"""The Heatmiser Neo base entity definitions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial
import logging
from typing import Any

from neohubapi.neohub import ATTR_SYSTEM, NeoHub, NeoStat, ScheduleFormat
from propcache import cached_property

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HeatmiserNeoConfigEntry, unique_id_is_mac
from .const import (
    DOMAIN,
    HEATMISER_HUB_PRODUCT_LIST,
    HEATMISER_PRODUCT_LIST,
    HEATMISER_TYPE_IDS_AWAY,
)
from .coordinator import HeatmiserNeoCoordinator
from .helpers import set_away, set_holiday

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class HeatmiserNeoEntityDescription(EntityDescription):
    """Describes Heatmiser Neo entity."""

    setup_filter_fn: Callable[[NeoStat, Any], bool] = lambda dev, sys_data: True
    availability_fn: Callable[[NeoStat], bool] = lambda device: not device.offline
    enabled_by_default_fn: Callable[[HeatmiserNeoEntity], bool] | None = None
    icon_fn: Callable[[NeoStat], str | None] | None = None
    # extra_attrs: list[str] | None = None
    custom_functions: (
        dict[
            str,
            Callable[[type[HeatmiserNeoEntity], ServiceCall], Awaitable[Any | None]],
        ]
        | None
    ) = None


@dataclass(frozen=True, kw_only=True)
class HeatmiserNeoHubEntityDescription(EntityDescription):
    """Describes Heatmiser Neo Hub entity."""

    setup_filter_fn: Callable[[HeatmiserNeoCoordinator], bool] = (
        lambda coordinator: True
    )
    enabled_by_default_fn: Callable[[HeatmiserNeoHubEntity], bool] | None = None
    icon_fn: Callable[[NeoStat], str | None] | None = None
    # extra_attrs: list[str] | None = None
    custom_functions: (
        dict[
            str,
            Callable[[type[HeatmiserNeoEntity], ServiceCall], Awaitable[Any | None]],
        ]
        | None
    ) = None


class HeatmiserNeoEntity(CoordinatorEntity[HeatmiserNeoCoordinator]):
    """Defines a base HeatmiserNeo entity."""

    entity_description: HeatmiserNeoEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        neodevice: NeoStat,
        coordinator: HeatmiserNeoCoordinator,
        hub: NeoHub,
        entity_description: HeatmiserNeoEntityDescription,
        config_entry: HeatmiserNeoConfigEntry,
    ) -> None:
        """Initialize the HeatmiserNeo entity."""
        super().__init__(coordinator)
        _LOGGER.debug(
            "Creating %s-%s for %s %s",
            type(self).__name__,
            entity_description.key,
            neodevice.name,
            neodevice.device_id,
        )
        self._key = entity_description.key
        self._neodevice = neodevice
        self._hub = hub
        self.entity_description = entity_description
        self._attr_should_poll = False
        self._attr_unique_id = (
            f"{config_entry.unique_id}_{self._neodevice.serial_number}_{self._key}"
        )

        via_device_identifier_key = DOMAIN
        if unique_id_is_mac(config_entry.unique_id):
            via_device_identifier_key = CONNECTION_NETWORK_MAC

        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{config_entry.unique_id}_{self._neodevice.serial_number}",
                )
            },
            name=self._neodevice.name,
            manufacturer="Heatmiser",
            model=f"{HEATMISER_PRODUCT_LIST[self.data.device_type]}",
            suggested_area=self._neodevice.name,
            serial_number=self._neodevice.serial_number,
            sw_version=self.data.stat_version,
            via_device=(via_device_identifier_key, config_entry.unique_id),
        )

    @property
    def data(self) -> NeoStat | None:
        """Helper to get the data for the current device."""
        (neo_devices, _) = self.coordinator.data
        return neo_devices.get(self._neodevice.name, None)

    @property
    def system_data(self):
        """Helper to get the data for the current device."""
        (_, all_data) = self.coordinator.data
        return all_data[ATTR_SYSTEM]

    @property
    def available(self):
        """Returns whether the entity is available or not."""
        if self.data:
            return self.entity_description.availability_fn(self.data)
        return False

    @property
    def extra_state_attributes(self):
        """Return the additional state attributes."""
        return {
            "device_id": self._neodevice.device_id,
            "device_type": self._neodevice.device_type,
            "offline": self.data.offline,
        }

    @property
    def icon(self) -> str | None:
        """Call icon function if defined."""
        if self.entity_description.icon_fn:
            return self.entity_description.icon_fn(self.data)
        return None

    @cached_property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added.

        This only applies when fist added to the entity registry.
        """
        if self.entity_description.enabled_by_default_fn:
            return self.entity_description.enabled_by_default_fn(self)
        return super().entity_registry_enabled_default

    async def call_custom_action(self, service_call: ServiceCall) -> Any | None:
        """Call a custom action specified in the entity description."""
        result = await self.entity_description.custom_functions.get(
            service_call.service
        )(self, service_call)
        self.coordinator.async_update_listeners()
        return result

    async def async_cancel_away_or_holiday(self) -> None:
        """Cancel away/holiday mode."""
        if _device_supports_away(self.data):
            dev = self.data
            if dev.away:
                await self._hub.set_away(False)
                self.coordinator.update_in_memory_state(
                    partial(set_away, False),
                    _device_supports_away,
                )
            if dev.holiday:
                await self._hub.cancel_holiday()
                self.coordinator.update_in_memory_state(
                    partial(set_holiday, False),
                    _device_supports_away,
                )

    async def async_set_away_mode(self) -> None:
        """Set away mode."""
        if _device_supports_away(self.data):
            dev = self.data
            if not (dev.away or dev.holiday):
                await self._hub.set_away(True)
                self.coordinator.update_in_memory_state(
                    partial(set_away, True), _device_supports_away
                )


class HeatmiserNeoHubEntity(CoordinatorEntity[HeatmiserNeoCoordinator]):
    """Defines a base HeatmiserNeoHub entity."""

    entity_description: HeatmiserNeoHubEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HeatmiserNeoCoordinator,
        hub: NeoHub,
        entity_description: HeatmiserNeoHubEntityDescription,
        config_entry: HeatmiserNeoConfigEntry,
    ) -> None:
        """Initialize the HeatmiserNeoHub entity."""
        super().__init__(coordinator)
        _LOGGER.debug(
            "Creating %s-%s",
            type(self).__name__,
            entity_description.key,
        )
        self._key = entity_description.key
        self._hub = hub
        self.entity_description = entity_description
        self._attr_should_poll = False
        self._attr_unique_id = f"{config_entry.unique_id}_{self._key}"

        identifier_key = DOMAIN
        if unique_id_is_mac(config_entry.unique_id):
            identifier_key = CONNECTION_NETWORK_MAC

        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    identifier_key,
                    config_entry.unique_id,
                )
            },
            name=f"NeoHub - {self._hub._host}",  # noqa: SLF001
            manufacturer="Heatmiser",
            model=f"{HEATMISER_HUB_PRODUCT_LIST[self.coordinator.system_data.HUB_TYPE]}",
            sw_version=self.coordinator.system_data.HUB_VERSION,
        )

    @property
    def available(self):
        """Returns whether the entity is available or not."""
        return True

    @property
    def icon(self) -> str | None:
        """Call icon function if defined."""
        if self.entity_description.icon_fn:
            return self.entity_description.icon_fn(self.data)
        return None

    @cached_property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added.

        This only applies when fist added to the entity registry.
        """
        if self.entity_description.enabled_by_default_fn:
            return self.entity_description.enabled_by_default_fn(self)
        return super().entity_registry_enabled_default

    async def call_custom_action(self, service_call: ServiceCall) -> Any | None:
        """Call a custom action specified in the entity description."""
        result = await self.entity_description.custom_functions.get(
            service_call.service
        )(self, service_call)
        self.coordinator.async_update_listeners()
        return result


async def call_custom_action(
    entity: HeatmiserNeoEntity, service_call: ServiceCall
) -> Any | None:
    """Call a custom action specified in the entity description."""
    if (
        not entity.entity_description.custom_functions
        or service_call.service not in entity.entity_description.custom_functions
    ):
        target_entities = service_call.data.get(ATTR_ENTITY_ID, None)
        if target_entities and entity.entity_id in target_entities:
            raise HomeAssistantError(
                f"Entity {entity.entity_id} does not support service"
            )
        return None
    return await entity.call_custom_action(service_call)


def _device_supports_away(dev: NeoStat) -> bool:
    return dev.device_type in HEATMISER_TYPE_IDS_AWAY


def profile_sensor_enabled_by_default(entity: HeatmiserNeoEntity) -> bool:
    """Determine if a profile entity should be enabled by default."""
    if (
        hasattr(entity.coordinator.system_data, "FORMAT")
        and entity.coordinator.system_data.FORMAT != ScheduleFormat.ZERO
    ):
        return True
    if (
        entity.data.time_clock_mode
        and hasattr(entity.coordinator.system_data, "ALT_TIMER_FORMAT")
        and entity.coordinator.system_data.ALT_TIMER_FORMAT != ScheduleFormat.ZERO
    ):
        return True
    return False
