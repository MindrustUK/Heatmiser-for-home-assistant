# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
"""Heatmiser Neo Number platform."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
from typing import Any

from neohubapi.neohub import NeoHub, NeoStat

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatmiserNeoConfigEntry
from .const import HEATMISER_TEMPERATURE_UNIT_HA_UNIT, HEATMISER_TYPE_IDS_THERMOSTAT
from .coordinator import HeatmiserNeoCoordinator
from .entity import HeatmiserNeoEntity, HeatmiserNeoEntityDescription

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class HeatmiserNeoNumberEntityDescription(
    HeatmiserNeoEntityDescription, NumberEntityDescription
):
    """Describes a number entity."""

    value_fn: Callable[[NeoStat], Any]
    set_value_fn: Callable[[HeatmiserNeoEntity, float], Awaitable[None]]
    unit_of_measurement_fn: Callable[[NeoStat, Any], Any] | None = None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatmiserNeoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Heatmiser Neo number entities."""
    hub = entry.runtime_data.hub
    coordinator = entry.runtime_data.coordinator

    if coordinator.data is None:
        _LOGGER.error("Coordinator data is None. Cannot set up button entities")
        return

    neo_devices, _ = coordinator.data
    system_data = coordinator.system_data

    _LOGGER.info("Adding Neo Device Numbers")

    async_add_entities(
        HeatmiserNeoNumber(neodevice, coordinator, hub, description, entry)
        for description in NUMBERS
        for neodevice in neo_devices.values()
        if description.setup_filter_fn(neodevice, system_data)
    )


async def async_set_frost_temperature(entity: HeatmiserNeoEntity, val: float) -> None:
    """Set the frost temperature on a device."""
    await entity.data.set_frost_temp(val)
    setattr(entity.data._data_, "FROST_TEMP", val)


async def async_set_output_delay(entity: HeatmiserNeoEntity, val: float) -> None:
    """Set the output delay on a device."""
    await entity.data.set_output_delay(int(val))
    setattr(entity.data._data_, "OUTPUT_DELAY", int(val))


async def async_set_floor_limit(entity: HeatmiserNeoEntity, val: float) -> None:
    """Set the floor limit temperature on a device."""
    await entity.data.set_floor_limit(int(val))
    setattr(entity.data._data_, "ENG_FLOOR_LIMIT", int(val))


async def async_set_user_limit(entity: HeatmiserNeoEntity, val: int) -> None:
    """Set the user limit temperature on a device."""
    await entity.data.set_user_limit(int(val))
    setattr(entity.data._data_, "USER_LIMIT", int(val))


NUMBERS: tuple[HeatmiserNeoNumberEntityDescription, ...] = (
    HeatmiserNeoNumberEntityDescription(
        key="heatmiser_neo_frost_temp",
        name="Frost Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT
            and not device.time_clock_mode
        ),
        value_fn=lambda dev: dev._data_.FROST_TEMP,
        set_value_fn=async_set_frost_temperature,
        unit_of_measurement_fn=lambda _, sys_data: (
            HEATMISER_TEMPERATURE_UNIT_HA_UNIT.get(sys_data.CORF, None)
        ),
        native_min_value=5,
        native_max_value=17,
        native_step=0.5,
        mode=NumberMode.BOX,
    ),
    HeatmiserNeoNumberEntityDescription(
        key="heatmiser_neo_output_delay",
        name="Output Delay",
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT
            and not device.time_clock_mode
        ),
        value_fn=lambda dev: dev._data_.OUTPUT_DELAY,
        set_value_fn=async_set_output_delay,
        native_min_value=0,
        native_max_value=15,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        mode=NumberMode.BOX,
    ),
    HeatmiserNeoNumberEntityDescription(
        key="heatmiser_neo_floor_limit_temp",
        name="Floor Limit Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT
            and not device.time_clock_mode
            and device.current_floor_temperature < 127
        ),
        value_fn=lambda dev: dev._data_.ENG_FLOOR_LIMIT,
        set_value_fn=async_set_floor_limit,
        native_step=1,
        unit_of_measurement_fn=lambda _, sys_data: (
            HEATMISER_TEMPERATURE_UNIT_HA_UNIT.get(sys_data.CORF, None)
        ),
        mode=NumberMode.BOX,
    ),
    HeatmiserNeoNumberEntityDescription(
        key="heatmiser_neo_user_limit",
        name="User Limit",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT
            and not device.time_clock_mode
        ),
        value_fn=lambda dev: dev._data_.USER_LIMIT,
        set_value_fn=async_set_user_limit,
        native_step=1,
        native_min_value=0,
        native_max_value=10,
        unit_of_measurement_fn=lambda _, sys_data: (
            HEATMISER_TEMPERATURE_UNIT_HA_UNIT.get(sys_data.CORF, None)
        ),
        mode=NumberMode.BOX,
    ),
)


class HeatmiserNeoNumber(HeatmiserNeoEntity, NumberEntity):
    """Heatmiser Neo number entity."""

    def __init__(
        self,
        neostat: NeoStat,
        coordinator: HeatmiserNeoCoordinator,
        hub: NeoHub,
        entity_description: HeatmiserNeoNumberEntityDescription,
        config_entry: HeatmiserNeoConfigEntry,
    ) -> None:
        """Initialize Heatmiser Neo number entity."""
        super().__init__(neostat, coordinator, hub, entity_description, config_entry)

    @property
    def native_value(self) -> float | None:
        """Return the entity value to represent the entity state."""
        return self.entity_description.value_fn(self.data)

    async def async_set_native_value(self, value: float) -> None:
        """Change the number."""
        await self.entity_description.set_value_fn(self, value)
        self.coordinator.async_update_listeners()

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        if self.entity_description.unit_of_measurement_fn:
            return self.entity_description.unit_of_measurement_fn(
                self.data, self.system_data
            )

        return self.entity_description.native_unit_of_measurement
