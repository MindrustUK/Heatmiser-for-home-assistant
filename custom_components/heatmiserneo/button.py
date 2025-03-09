# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
"""Heatmiser Neo Button platform."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging

from neohubapi.neohub import NeoHub, NeoStat

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatmiserNeoConfigEntry
from .const import HEATMISER_TYPE_IDS_IDENTIFY, HEATMISER_TYPE_IDS_REPEATER
from .coordinator import HeatmiserNeoCoordinator
from .entity import (
    HeatmiserNeoEntity,
    HeatmiserNeoEntityDescription,
    HeatmiserNeoHubEntity,
    HeatmiserNeoHubEntityDescription,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatmiserNeoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Heatmiser Neo button entities."""
    hub = entry.runtime_data.hub
    coordinator = entry.runtime_data.coordinator

    if coordinator.data is None:
        _LOGGER.error("Coordinator data is None. Cannot set up button entities")
        return

    neo_devices, _ = coordinator.data
    system_data = coordinator.system_data

    _LOGGER.info("Adding Neo Device Buttons")

    async_add_entities(
        HeatmiserNeoHubButton(coordinator, hub, description, entry)
        for description in HUB_BUTTONS
        if description.setup_filter_fn(coordinator)
    )

    async_add_entities(
        HeatmiserNeoButton(neodevice, coordinator, hub, description, entry)
        for description in BUTTONS
        for neodevice in neo_devices.values()
        if description.setup_filter_fn(neodevice, system_data)
    )


_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class HeatmiserNeoButtonEntityDescription(
    HeatmiserNeoEntityDescription, ButtonEntityDescription
):
    """Describes a button entity."""

    press_fn: Callable[[HeatmiserNeoEntity], Awaitable[None]]


@dataclass(frozen=True, kw_only=True)
class HeatmiserNeoHubButtonEntityDescription(
    HeatmiserNeoHubEntityDescription, ButtonEntityDescription
):
    """Describes a button entity."""

    press_fn: Callable[[HeatmiserNeoCoordinator], Awaitable[None]]


async def async_remove_repeater(entity: HeatmiserNeoEntity):
    """Handle repeater removal."""
    return await entity.coordinator.hub.remove_repeater(entity.data.device_id)


BUTTONS: tuple[HeatmiserNeoButtonEntityDescription, ...] = (
    HeatmiserNeoButtonEntityDescription(
        key="heatmiser_neo_identify_button",
        device_class=ButtonDeviceClass.IDENTIFY,
        entity_category=EntityCategory.DIAGNOSTIC,
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_IDENTIFY
        ),
        press_fn=lambda dev: dev.data.identify(),
    ),
    HeatmiserNeoButtonEntityDescription(
        key="heatmiser_repeater_remove",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        name="Remove",
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_REPEATER
        ),
        press_fn=async_remove_repeater,
    ),
)


HUB_BUTTONS: tuple[HeatmiserNeoHubButtonEntityDescription, ...] = (
    HeatmiserNeoHubButtonEntityDescription(
        key="heatmiser_neohub_identify_button",
        device_class=ButtonDeviceClass.IDENTIFY,
        entity_category=EntityCategory.DIAGNOSTIC,
        press_fn=lambda coordinator: coordinator.hub.identify(),
    ),
)


class HeatmiserNeoButton(HeatmiserNeoEntity, ButtonEntity):
    """Heatmiser Neo button entity."""

    def __init__(
        self,
        neostat: NeoStat,
        coordinator: HeatmiserNeoCoordinator,
        hub: NeoHub,
        entity_description: HeatmiserNeoButtonEntityDescription,
        config_entry: HeatmiserNeoConfigEntry,
    ) -> None:
        """Initialize Heatmiser Neo button entity."""
        super().__init__(neostat, coordinator, hub, entity_description, config_entry)

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.entity_description.press_fn(self)


class HeatmiserNeoHubButton(HeatmiserNeoHubEntity, ButtonEntity):
    """Heatmiser Neo button entity."""

    def __init__(
        self,
        coordinator: HeatmiserNeoCoordinator,
        hub: NeoHub,
        entity_description: HeatmiserNeoButtonEntityDescription,
        config_entry: HeatmiserNeoConfigEntry,
    ) -> None:
        """Initialize Heatmiser Neo button entity."""
        super().__init__(coordinator, hub, entity_description, config_entry)

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.entity_description.press_fn(self.coordinator)
