# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""Heatmiser Neo Select entities via Heatmiser Neo-hub."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Final

from neohubapi.neohub import NeoHub, NeoStat

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DEFAULTS,
    CONF_TIMER_HOLD_DURATION,
    CONF_TIMER_OPTIONS,
    DEFAULT_TIMER_HOLD_DURATION,
    HEATMISER_TYPE_IDS_PLUG,
    HEATMISER_TYPE_IDS_THERMOSTAT,
    HEATMISER_TYPE_IDS_THERMOSTAT_NOT_HC,
    HEATMISER_TYPE_IDS_TIMER,
    PROFILE_0,
    ModeSelectOption,
)
from .coordinator import HeatmiserNeoConfigEntry, HeatmiserNeoCoordinator
from .entity import (
    HeatmiserNeoEntity,
    HeatmiserNeoEntityDescription,
    HeatmiserNeoHubEntity,
    HeatmiserNeoHubEntityDescription,
    async_setup_entities,
    profile_sensor_enabled_by_default,
)
from .helpers import async_cancel_away_or_holiday, async_set_away_mode

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class HeatmiserNeoSelectEntityDescription(
    HeatmiserNeoEntityDescription, SelectEntityDescription
):
    """Class to describe an Heatmiser Neo select entity."""

    value_fn: Callable[[HeatmiserNeoEntity], str | None]
    set_value_fn: Callable[[str, HeatmiserNeoEntity], Awaitable[None]]
    options_fn: Callable[[HeatmiserNeoEntity], list[str]] | None = None


@dataclass(frozen=True, kw_only=True)
class HeatmiserNeoHubSelectEntityDescription(
    HeatmiserNeoHubEntityDescription, SelectEntityDescription
):
    """Class to describe an Heatmiser Neo select entity."""

    value_fn: Callable[[HeatmiserNeoCoordinator], str]
    set_value_fn: Callable[[str, HeatmiserNeoHubEntity], Awaitable[None]]


async def set_timer_auto(entity: HeatmiserNeoEntity):
    """Set device back to auto based on its current state."""
    dev = entity.data
    assert entity.coordinator.config_entry
    if dev.standby:
        await set_timer_standby(entity.coordinator.config_entry, dev, False)
    if dev.hold_on:
        await set_timer_override(
            entity.coordinator.config_entry, dev, dev.hold_temp == 1, 0
        )
    await async_cancel_away_or_holiday(
        entity.coordinator.config_entry.runtime_data.coordinator, dev
    )


async def set_timer_away(entity: HeatmiserNeoEntity):
    """Set device back to auto based on its current state."""
    dev = entity.data
    assert entity.coordinator.config_entry
    if dev.standby:
        await set_timer_standby(entity.coordinator.config_entry, dev, False)
    if dev.hold_on:
        await set_timer_override(
            entity.coordinator.config_entry, dev, dev.hold_temp == 1, 0
        )
    await async_set_away_mode(
        entity.coordinator.config_entry.runtime_data.coordinator, dev
    )


async def set_timer_override(
    config_entry: HeatmiserNeoConfigEntry,
    dev: NeoStat,
    on: bool,
    duration: int | None = None,
):
    """Set timer override."""
    if duration is None:
        duration = (
            config_entry.options.get(CONF_DEFAULTS, {})
            .get(CONF_TIMER_OPTIONS, {})
            .get(CONF_TIMER_HOLD_DURATION, DEFAULT_TIMER_HOLD_DURATION)
        )
    assert duration is not None
    state = duration > 0
    if state:
        await async_cancel_away_or_holiday(config_entry.runtime_data.coordinator, dev)
        if on and dev.standby:
            await set_timer_standby(config_entry, dev, False)
    await dev.set_timer_hold(on, duration)
    dev.hold_on = state
    if state:
        dev.timer_on = on
        dev.hold_temp = 1 if on else 0
    dev.hold_time = timedelta(minutes=duration)


async def set_timer_standby(
    config_entry: HeatmiserNeoConfigEntry, dev: NeoStat, state: bool = True
):
    """Set standby mode. Disable hold if set."""
    if state and dev.hold_on:
        await set_timer_override(config_entry, dev, dev.hold_temp == 1, 0)
    await dev.set_frost(state)
    dev.standby = state
    if dev.standby:
        dev.timer_on = False


async def set_plug_auto(entity: HeatmiserNeoEntity):
    """Set device back to auto based on its current state."""
    dev = entity.data
    assert entity.coordinator.config_entry
    await set_plug_override(entity.coordinator.config_entry, dev, dev.hold_temp == 1, 0)
    await async_cancel_away_or_holiday(
        entity.coordinator.config_entry.runtime_data.coordinator, dev
    )


# async def set_plug_away(entity: HeatmiserNeoSelectEntity):
#     """Set device back to auto based on its current state."""
#     dev = entity.data
#     set_plug_override(entity, dev.hold_temp == 1, 0)
#     await entity.async_set_away_mode()


async def set_plug_override(
    config_entry: HeatmiserNeoConfigEntry,
    dev: NeoStat,
    on: bool,
    duration: int | None = None,
    turn_off_manual: bool = True,
):
    """Set timer override. Disable manual if set."""
    if duration is None:
        duration = (
            config_entry.options.get(CONF_DEFAULTS, {})
            .get(CONF_TIMER_OPTIONS, {})
            .get(CONF_TIMER_HOLD_DURATION, DEFAULT_TIMER_HOLD_DURATION)
        )
    hub = config_entry.runtime_data.hub
    assert duration is not None
    state = duration > 0
    if turn_off_manual and not dev.manual_off:
        await hub.set_manual(False, [dev])
        dev.manual_off = True
    if state:
        await async_cancel_away_or_holiday(config_entry.runtime_data.coordinator, dev)
    await dev.set_timer_hold(on, duration)
    dev.hold_on = state
    if state:
        dev.timer_on = on
        dev.hold_temp = 1 if on else 0
    dev.hold_time = timedelta(minutes=duration)


async def set_plug_manual(entity: HeatmiserNeoSelectEntity, on: bool):
    """Set standby mode. Disable hold if set."""
    dev = entity.data
    hub = entity.coordinator.hub
    assert entity.coordinator.config_entry
    await set_plug_override(
        entity.coordinator.config_entry, dev, dev.hold_temp == 1, 0, False
    )
    if dev.manual_off:
        await hub.set_manual(True, [dev])
        dev.manual_off = False
    if on != dev.timer_on:
        await hub.set_timer(on, [dev])
        dev.timer_on = on


def _timer_mode(device: NeoStat) -> ModeSelectOption:
    """Decode the timer mode."""
    # If Hub Away, Device can be on standby
    # Else if device on Standby, Hold can be enabled
    if device.away or device.holiday:
        if device.standby:
            return ModeSelectOption.STANDBY
        return ModeSelectOption.AWAY
    if device.hold_on:
        if device.hold_temp == 1:
            return ModeSelectOption.OVERRIDE_ON
        return ModeSelectOption.OVERRIDE_OFF
    if device.standby:
        return ModeSelectOption.STANDBY
    return ModeSelectOption.AUTO


def _dst_mode(coordinator: HeatmiserNeoCoordinator) -> str:
    tzstr = coordinator.system_data.TIMEZONESTR
    if not coordinator.system_data.DST_AUTO or tzstr == "":
        if coordinator.system_data.DST_ON:
            return "On"
        return "Off"
    tzstr = coordinator.system_data.TIMEZONESTR
    if not tzstr:
        return "UK"
    return tzstr


async def async_set_dst_mode(coordinator: HeatmiserNeoCoordinator, option: str):
    """Update the DST mode."""
    if option in ("Off", "On"):
        dst_on = option == "On"
        await async_set_dst(coordinator)
        await coordinator.hub.manual_dst(dst_on)
        setattr(coordinator.system_data, "DST_AUTO", False)
        setattr(coordinator.system_data, "DST_ON", dst_on)
        setattr(coordinator.system_data, "TIMEZONESTR", "")
    else:
        await async_set_dst(coordinator, option)
        setattr(coordinator.system_data, "DST_AUTO", True)
        setattr(coordinator.system_data, "TIMEZONESTR", option)


def _timer_icon(device: NeoStat) -> str | None:
    if device.away or device.holiday:
        if device.standby:
            return "mdi:timer-off-outline"
        return "mdi:account-arrow-right"
    if device.hold_on:
        if device.hold_temp == 1:
            return "mdi:timer-stop"
        return "mdi:timer-stop-outline"
    if device.standby:
        return "mdi:timer-off-outline"
    return "mdi:timer" if device.timer_on else "mdi:timer-outline"


def _plug_mode(device: NeoStat) -> ModeSelectOption:
    if not device.manual_off:
        if device.timer_on:
            return ModeSelectOption.MANUAL_ON
        return ModeSelectOption.MANUAL_OFF
    # if device.away or device.holiday:
    #     return ModeSelectOption.AWAY
    if device.hold_on:
        if device.hold_temp == 1:
            return ModeSelectOption.OVERRIDE_ON
        return ModeSelectOption.OVERRIDE_OFF
    return ModeSelectOption.AUTO


def _plug_icon(device: NeoStat) -> str | None:
    if not device.manual_off:
        if device.timer_on:
            return "mdi:toggle-switch-variant"
        return "mdi:toggle-switch-variant-off"
    if device.hold_on:
        if device.hold_temp == 1:
            return "mdi:timer-stop"
        return "mdi:timer-stop-outline"
    return "mdi:timer" if device.timer_on else "mdi:timer-outline"


async def async_set_switching_differential(
    val: str, entity: HeatmiserNeoEntity
) -> None:
    """Set the switching differential on a device."""
    await entity.data.set_diff(int(val))
    setattr(entity.data._data_, "SWITCHING DIFFERENTIAL", int(val))


async def async_set_preheat(
    val: str,
    entity: HeatmiserNeoEntity,
) -> None:
    """Set the maximum preheat time on a device."""
    await entity.data.set_preheat(int(val))
    setattr(entity.data._data_, "MAX_PREHEAT", int(val))


async def async_set_profile(
    val: str,
    entity: HeatmiserNeoEntity,
) -> None:
    """Set the maximum preheat time on a device."""
    profile_id = _profile_name_to_id(entity.coordinator, val)
    await async_base_set_profile(profile_id, entity)


async def async_set_timer_profile(
    val: str,
    entity: HeatmiserNeoEntity,
) -> None:
    """Set the maximum preheat time on a device."""
    profile_id = _timer_profile_name_to_id(entity.coordinator, val)
    await async_base_set_profile(profile_id, entity)


async def async_base_set_profile(
    profile_id: int,
    entity: HeatmiserNeoEntity,
) -> None:
    """Set the maximum preheat time on a device."""
    if profile_id == 0:
        await entity.data.clear_profile_id()
    else:
        await entity.data.set_profile_id(profile_id)
    entity.data.active_profile = profile_id


TIMER_SET_MODE = {
    ModeSelectOption.AUTO: set_timer_auto,
    ModeSelectOption.OVERRIDE_ON: lambda entity: set_timer_override(
        entity.coordinator.config_entry, entity.data, True
    ),
    ModeSelectOption.OVERRIDE_OFF: lambda entity: set_timer_override(
        entity.coordinator.config_entry, entity.data, False
    ),
    ModeSelectOption.STANDBY: set_timer_standby,
    ModeSelectOption.AWAY: set_timer_away,
}

PLUG_SET_MODE = {
    ModeSelectOption.AUTO: set_plug_auto,
    ModeSelectOption.OVERRIDE_ON: lambda entity: set_plug_override(
        entity.coordinator.config_entry, entity.data, True
    ),
    ModeSelectOption.OVERRIDE_OFF: lambda entity: set_plug_override(
        entity.coordinator.config_entry, entity.data, False
    ),
    ModeSelectOption.MANUAL_ON: lambda entity: set_plug_manual(entity, True),
    ModeSelectOption.MANUAL_OFF: lambda entity: set_plug_manual(entity, False),
    # ModeSelectOption.AWAY: set_plug_away,
}


def _timer_set_mode(mode: str, entity: HeatmiserNeoEntity) -> Awaitable[None]:
    function = TIMER_SET_MODE.get(ModeSelectOption(mode))
    assert function
    return function(entity)


def _plug_set_mode(mode: str, entity: HeatmiserNeoEntity) -> Awaitable[None]:
    function = PLUG_SET_MODE.get(ModeSelectOption(mode))
    assert function
    return function(entity)


SELECT: Final[tuple[HeatmiserNeoSelectEntityDescription, ...]] = (
    HeatmiserNeoSelectEntityDescription(
        key="heatmiser_neo_timer_mode_select",
        name=None,  # This is the main entity of the device
        options=[c.value.lower() for c in TIMER_SET_MODE],
        setup_filter_fn=lambda device, _: (
            device.device_type
            in HEATMISER_TYPE_IDS_TIMER.difference(HEATMISER_TYPE_IDS_PLUG)
            and device.time_clock_mode
        ),
        value_fn=lambda entity: _timer_mode(entity.data).value,
        set_value_fn=_timer_set_mode,
        icon_fn=_timer_icon,
        translation_key="timer_mode",
    ),
    HeatmiserNeoSelectEntityDescription(
        key="heatmiser_neo_plug_mode_select",
        name=None,  # This is the main entity of the device
        options=[c.value.lower() for c in PLUG_SET_MODE],
        setup_filter_fn=lambda device, _: device.device_type in HEATMISER_TYPE_IDS_PLUG,
        value_fn=lambda entity: _plug_mode(entity.data).value,
        set_value_fn=_plug_set_mode,
        icon_fn=_plug_icon,
        translation_key="plug_mode",
    ),
    HeatmiserNeoSelectEntityDescription(
        key="heatmiser_neo_switching_differential",
        options=[str(n) for n in range(4)],
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT
            and not device.time_clock_mode
        ),
        value_fn=lambda entity: str(
            getattr(entity.data._data_, "SWITCHING DIFFERENTIAL")
        ),
        property_exists_fn=lambda device: hasattr(
            device._data_, "SWITCHING DIFFERENTIAL"
        ),
        set_value_fn=async_set_switching_differential,
        translation_key="switching_differential",
    ),
    HeatmiserNeoSelectEntityDescription(
        key="heatmiser_neo_preheat_time",
        options=[str(n) for n in range(6)],
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT
            and not device.time_clock_mode
        ),
        value_fn=lambda entity: str(entity.data._data_.MAX_PREHEAT),
        property_exists_fn=lambda device: hasattr(device._data_, "MAX_PREHEAT"),
        set_value_fn=async_set_preheat,
        translation_key="preheat_time",
    ),
    HeatmiserNeoSelectEntityDescription(
        key="heatmiser_neo_active_profile",
        options_fn=lambda entity: _profile_names(entity.coordinator),
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT_NOT_HC
            and not device.time_clock_mode
        ),
        value_fn=lambda entity: _profile_id_to_name(
            entity.data.active_profile, entity.coordinator
        ),
        set_value_fn=async_set_profile,
        name="Active Profile",
        enabled_by_default_fn=profile_sensor_enabled_by_default,
    ),
    HeatmiserNeoSelectEntityDescription(
        key="heatmiser_neo_active_timer_profile",
        options_fn=lambda entity: _timer_profile_names(entity.coordinator),
        setup_filter_fn=lambda device, _: (
            device.device_type in HEATMISER_TYPE_IDS_THERMOSTAT_NOT_HC
            and device.time_clock_mode
        ),
        value_fn=lambda entity: _profile_id_to_name(
            entity.data.active_profile, entity.coordinator
        ),
        set_value_fn=async_set_timer_profile,
        name="Active Profile",
        enabled_by_default_fn=profile_sensor_enabled_by_default,
    ),
)

HUB_SELECT: Final[tuple[HeatmiserNeoHubSelectEntityDescription, ...]] = (
    HeatmiserNeoHubSelectEntityDescription(
        key="heatmiser_neohub_dst_rule",
        name="DST Rule",
        options=["UK", "EU", "NZ", "Off", "On"],
        value_fn=_dst_mode,
        set_value_fn=lambda mode, entity: async_set_dst_mode(entity.coordinator, mode),
    ),
    HeatmiserNeoHubSelectEntityDescription(
        key="heatmiser_neohub_time_zone",
        # name="DST Rule",
        options=[
            "tz-1200",
            "tz-1100",
            "tz-1000",
            "tz-950",
            "tz-900",
            "tz-800",
            "tz-700",
            "tz-600",
            "tz-500",
            "tz-400",
            "tz-350",
            "tz-300",
            "tz-200",
            "tz-100",
            "tz0",
            "tz100",
            "tz200",
            "tz300",
            "tz350",
            "tz400",
            "tz450",
            "tz500",
            "tz550",
            "tz575",
            "tz600",
            "tz650",
            "tz700",
            "tz800",
            "tz875",
            "tz900",
            "tz950",
            "tz100",
            "tz1050",
            "tz1100",
            "tz1200",
            "tz1275",
            "tz1300",
            "tz1400",
        ],
        value_fn=lambda coordinator: f"tz{(coordinator.system_data.TIME_ZONE * 100):g}",
        set_value_fn=lambda timezone, entity: async_set_timezone(
            entity.coordinator, timezone
        ),
        translation_key="time_zone",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatmiserNeoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Heatmiser Neo select entities."""
    hub = entry.runtime_data.hub
    coordinator = entry.runtime_data.coordinator

    if coordinator.data is None:
        _LOGGER.error("Coordinator data is None. Cannot set up button entities")
        return

    @callback
    def hub_entities():
        return [
            HeatmiserNeoHubSelectEntity(coordinator, hub, description, entry)
            for description in HUB_SELECT
            if description.setup_filter_fn(coordinator)
        ]

    @callback
    def device_entities(new_devices: list[NeoStat]):
        return [
            HeatmiserNeoSelectEntity(neodevice, coordinator, hub, description, entry)
            for description in SELECT
            for neodevice in new_devices
            if description.setup_filter_fn(neodevice, coordinator.system_data)
        ]

    await async_setup_entities(
        hass, entry, async_add_entities, Platform.SELECT, hub_entities, device_entities
    )


class HeatmiserNeoSelectEntity(
    HeatmiserNeoEntity[HeatmiserNeoSelectEntityDescription], SelectEntity
):
    """Define an Heatmiser Neo select."""

    entity_description: HeatmiserNeoSelectEntityDescription

    def __init__(
        self,
        neostat: NeoStat,
        coordinator: HeatmiserNeoCoordinator,
        hub: NeoHub,
        entity_description: HeatmiserNeoSelectEntityDescription,
        config_entry: HeatmiserNeoConfigEntry,
    ) -> None:
        """Initialize Heatmiser Neo select entity."""
        super().__init__(neostat, coordinator, hub, entity_description, config_entry)
        if entity_description.options_fn:
            self._attr_options = entity_description.options_fn(self)
        if self.available:
            self._attr_current_option = entity_description.value_fn(self)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.entity_description.set_value_fn(option, self)
        self.coordinator.async_update_listeners()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.entity_description.options_fn:
            self._attr_options = self.entity_description.options_fn(self)
        if self.available:
            self._attr_current_option = self.entity_description.value_fn(self)
        super()._handle_coordinator_update()


class HeatmiserNeoHubSelectEntity(
    HeatmiserNeoHubEntity[HeatmiserNeoHubSelectEntityDescription], SelectEntity
):
    """Define an Heatmiser Neo Hub select."""

    entity_description: HeatmiserNeoHubSelectEntityDescription

    def __init__(
        self,
        coordinator: HeatmiserNeoCoordinator,
        hub: NeoHub,
        entity_description: HeatmiserNeoHubSelectEntityDescription,
        config_entry: HeatmiserNeoConfigEntry,
    ) -> None:
        """Initialize Heatmiser Neo select entity."""
        super().__init__(coordinator, hub, entity_description, config_entry)
        self._attr_current_option = entity_description.value_fn(coordinator)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.entity_description.set_value_fn(option, self)
        self.coordinator.async_update_listeners()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_current_option = self.entity_description.value_fn(self.coordinator)
        super()._handle_coordinator_update()


async def async_set_dst(
    coordinator: HeatmiserNeoCoordinator, region: str | None = None
) -> None:
    """Set DST mode."""
    state = region is not None
    await coordinator.hub.set_dst(state, region)


async def async_set_timezone(
    coordinator: HeatmiserNeoCoordinator, timezone: str
) -> None:
    """Set TimeZone."""
    await coordinator.hub.set_timezone(round(float(timezone[2:]) / 100, 2))


def _profile_id_to_name(profile_id, coordinator: HeatmiserNeoCoordinator) -> str | None:
    """Convert a profile id to a name."""
    if profile_id == 0:
        return PROFILE_0
    profile = coordinator.profiles.get(int(profile_id))
    if profile:
        return profile.name
    profile = coordinator.timer_profiles.get(int(profile_id))
    if profile:
        return profile.name
    return None


def _profile_names(coordinator: HeatmiserNeoCoordinator) -> list[str]:
    """Convert a profile id to a name."""
    names = [p.name for p in coordinator.profiles.values()]
    names.insert(0, PROFILE_0)
    return names


def _timer_profile_names(coordinator: HeatmiserNeoCoordinator) -> list[str]:
    """Convert a profile id to a name."""
    names = [p.name for p in coordinator.timer_profiles.values()]
    names.insert(0, PROFILE_0)
    return names


def _profile_name_to_id(coordinator: HeatmiserNeoCoordinator, option: str) -> int:
    """Convert a profile id to a name."""
    if option == PROFILE_0:
        return 0
    profiles = [k for k, v in coordinator.profiles.items() if v.name == option]
    return profiles[0]


def _timer_profile_name_to_id(coordinator: HeatmiserNeoCoordinator, option: str) -> int:
    """Convert a profile id to a name."""
    if option == PROFILE_0:
        return 0
    profiles = [k for k, v in coordinator.timer_profiles.items() if v.name == option]
    return profiles[0]
