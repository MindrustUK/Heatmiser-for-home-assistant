# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""Heatmiser Neo Binary Sensors via Heatmiser Neo-hub."""

from collections.abc import Callable
from dataclasses import dataclass
import logging

from neohubapi.neohub import NeoHub, NeoStat

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatmiserNeoConfigEntry
from .coordinator import HeatmiserNeoCoordinator
from .entity import (
    HeatmiserNeoEntityDescription,
    HeatmiserNeoHubEntity,
    HeatmiserNeoHubEntityDescription,
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
        _LOGGER.error("Coordinator data is None. Cannot set up sensor entities")
        return

    _LOGGER.info("Adding Neo Switches")

    async_add_entities(
        HeatmiserNeoHubSwitch(coordinator, hub, description, entry)
        for description in HUB_SWITCHES
        if description.setup_filter_fn(coordinator)
    )


@dataclass(frozen=True, kw_only=True)
class HeatmiserNeoSwitchEntityDescription(
    HeatmiserNeoEntityDescription, SwitchEntityDescription
):
    """Describes a button entity."""

    value_fn: Callable[[NeoStat], bool]


@dataclass(frozen=True, kw_only=True)
class HeatmiserNeoHubSwitchEntityDescription(
    HeatmiserNeoHubEntityDescription, SwitchEntityDescription
):
    """Describes a button entity."""

    value_fn: Callable[[HeatmiserNeoCoordinator], bool]


HUB_SWITCHES: tuple[HeatmiserNeoHubSwitchEntityDescription, ...] = (
    HeatmiserNeoHubSwitchEntityDescription(
        key="heatmiser_neohub_ntp_on",
        name="NTP",
        value_fn=lambda coordinator: coordinator.system_data.NTP_ON == "Running",
    ),
)


class HeatmiserNeoHubSwitch(HeatmiserNeoHubEntity, SwitchEntity):
    """Heatmiser Neo binary entity."""

    def __init__(
        self,
        coordinator: HeatmiserNeoCoordinator,
        hub: NeoHub,
        entity_description: HeatmiserNeoHubSwitchEntityDescription,
        config_entry: HeatmiserNeoConfigEntry,
    ) -> None:
        """Initialize Heatmiser Neo binary entity."""
        super().__init__(coordinator, hub, entity_description, config_entry)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.entity_description.value_fn(self.coordinator)

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._hub.set_ntp(True)
        setattr(self.coordinator.system_data, "NTP_ON", "Running")
        self.coordinator.async_update_listeners()

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._hub.set_ntp(False)
        setattr(self.coordinator.system_data, "NTP_ON", "Stopped")
        self.coordinator.async_update_listeners()
