# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
"""The Heatmiser Neo base entity definitions."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import logging
from typing import Any, Generic, TypeVar

from neohubapi.neohub import ATTR_SYSTEM, NeoHub, NeoStat, ScheduleFormat
from propcache.api import cached_property

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.helpers.entity_registry as er
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    HEATMISER_HUB_PRODUCT_LIST,
    HEATMISER_PRODUCT_LIST,
    HEATMISER_TYPE_IDS_PLUG,
)
from .coordinator import HeatmiserNeoConfigEntry, HeatmiserNeoCoordinator
from .utils import unique_id_is_mac

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class HeatmiserNeoEntityDescription(EntityDescription):
    """Describes Heatmiser Neo entity."""

    setup_filter_fn: Callable[[NeoStat, Any], bool] = lambda dev, sys_data: True
    availability_fn: Callable[[NeoStat], bool] = lambda device: not device.offline
    property_exists_fn: Callable[[NeoStat], bool] = lambda device: True
    enabled_by_default_fn: Callable[[HeatmiserNeoEntity], bool] | None = None
    icon_fn: Callable[[NeoStat], str | None] | None = None


@dataclass(frozen=True, kw_only=True)
class HeatmiserNeoHubEntityDescription(EntityDescription):
    """Describes Heatmiser Neo Hub entity."""

    setup_filter_fn: Callable[[HeatmiserNeoCoordinator], bool] = (
        lambda coordinator: True
    )
    enabled_by_default_fn: Callable[[HeatmiserNeoHubEntity], bool] | None = None
    icon_fn: Callable[[], str | None] | None = None


DescriptionT = TypeVar("DescriptionT", bound=HeatmiserNeoEntityDescription)
HubDescriptionT = TypeVar("HubDescriptionT", bound=HeatmiserNeoHubEntityDescription)


class HeatmiserNeoEntity(
    CoordinatorEntity[HeatmiserNeoCoordinator], Generic[DescriptionT]
):
    """Defines a base HeatmiserNeo entity."""

    entity_description: DescriptionT
    _attr_has_entity_name = True

    def __init__(
        self,
        neodevice: NeoStat,
        coordinator: HeatmiserNeoCoordinator,
        hub: NeoHub,
        entity_description: DescriptionT,
        config_entry: HeatmiserNeoConfigEntry,
    ) -> None:
        """Initialize the HeatmiserNeo entity."""
        super().__init__(coordinator)
        assert config_entry.unique_id
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

        model_id = (
            f"{self._neodevice.device_type}-TIMER"
            if self._neodevice.time_clock_mode
            and self._neodevice.device_type not in HEATMISER_TYPE_IDS_PLUG
            else self._neodevice.device_type
        )
        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{config_entry.unique_id}_{self._neodevice.serial_number}",
                )
            },
            name=self._neodevice.name,
            manufacturer="Heatmiser",
            model=f"{HEATMISER_PRODUCT_LIST[self._neodevice.device_type]}",
            model_id=model_id,
            suggested_area=self._neodevice.name,
            serial_number=self._neodevice.serial_number,
            sw_version=self._neodevice.stat_version,
            via_device=(via_device_identifier_key, config_entry.unique_id),
        )

    @property
    def data(self) -> NeoStat:
        """Helper to get the data for the current device."""
        (neo_devices, _) = self.coordinator.data
        device = neo_devices.get(self._neodevice.name)
        assert device
        return device

    @property
    def system_data(self):
        """Helper to get the data for the current device."""
        (_, all_data) = self.coordinator.data
        return all_data[ATTR_SYSTEM]

    @property
    def available(self):
        """Returns whether the entity is available or not."""
        neo_devices, _ = self.coordinator.data
        if neo_devices.get(
            self._neodevice.name, None
        ) and self.entity_description.property_exists_fn(self.data):
            return self.entity_description.availability_fn(self.data)
        return False

    @property
    def extra_state_attributes(self):
        """Return the additional state attributes."""
        return {
            "device_id": self._neodevice.device_id,
            "device_type": self._neodevice.device_type,
            "offline": self.data.offline if self.data else True,
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


class HeatmiserNeoHubEntity(
    CoordinatorEntity[HeatmiserNeoCoordinator], Generic[HubDescriptionT]
):
    """Defines a base HeatmiserNeoHub entity."""

    entity_description: HubDescriptionT
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HeatmiserNeoCoordinator,
        hub: NeoHub,
        entity_description: HubDescriptionT,
        config_entry: HeatmiserNeoConfigEntry,
    ) -> None:
        """Initialize the HeatmiserNeoHub entity."""
        super().__init__(coordinator)
        assert config_entry.unique_id
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
            return self.entity_description.icon_fn()
        return None

    @cached_property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added.

        This only applies when fist added to the entity registry.
        """
        if self.entity_description.enabled_by_default_fn:
            return self.entity_description.enabled_by_default_fn(self)
        return super().entity_registry_enabled_default


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


async def async_setup_entities(
    hass: HomeAssistant,
    entry: HeatmiserNeoConfigEntry,
    async_add_entities: AddEntitiesCallback,
    domain: Platform,
    hub_entity_callback: Callable[[], Sequence[HeatmiserNeoHubEntity]] | None,
    device_entity_callback: Callable[[list[NeoStat]], Sequence[HeatmiserNeoEntity]]
    | None,
) -> None:
    """Set up Heatmiser Neo button entities."""
    coordinator = entry.runtime_data.coordinator
    entity_registry = er.async_get(hass)

    devices_added: set[str] = set()
    entities_added: set[str] = set()

    if hub_entity_callback:
        _LOGGER.info("Adding %s %s hub entities", DOMAIN, domain)
        hub_entities = hub_entity_callback()
        async_add_entities(hub_entities)
        entities_added |= {
            entity.unique_id for entity in hub_entities if entity.unique_id
        }
    if device_entity_callback:

        @callback
        def add_entities() -> None:
            nonlocal devices_added
            nonlocal entities_added

            neo_devices, _ = coordinator.data

            new_devices = [
                dev
                for dev in neo_devices.values()
                if dev.serial_number not in devices_added
            ]
            if new_devices:
                _LOGGER.info("Adding %s %s entities", DOMAIN, domain)
                entities = device_entity_callback(new_devices)
                async_add_entities(entities)
                devices_added |= {dev.serial_number for dev in new_devices}
                entities_added |= {
                    entity.unique_id for entity in entities if entity.unique_id
                }
            if len(devices_added) > len(neo_devices):
                devices_added.clear()
                devices_added |= {dev.serial_number for dev in neo_devices.values()}

        entry.async_on_unload(coordinator.async_add_listener(add_entities))
        add_entities()

    deleted_entries = {
        entity.entity_id: entity.device_id
        for entity in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
        if entity.domain == domain
        and entity.platform == DOMAIN
        and entity.unique_id
        and entity.unique_id not in entities_added
    }

    for entity_id in deleted_entries:
        entity_registry.async_remove(entity_id)

    modified_devices = {
        device_id for device_id in deleted_entries.values() if device_id
    }

    device_registry = dr.async_get(hass)
    for device_id in modified_devices:
        device_entities = er.async_entries_for_device(entity_registry, device_id)
        if len(device_entities) == 0:
            device_registry.async_update_device(
                device_id=device_id,
                remove_config_entry_id=entry.entry_id,
            )
