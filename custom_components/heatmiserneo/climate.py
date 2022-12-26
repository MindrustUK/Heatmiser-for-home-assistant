
# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only

"""
homeassistant.components.climate.heatmiserneo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Heatmiser NeoStat control via Heatmiser Neo-hub
"""

import logging
import asyncio

import voluptuous as vol
 
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    HVAC_MODE_COOL,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_RANGE
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from neohubapi.neohub import NeoHub, NeoStat, HCMode
from .const import DOMAIN, HUB, COORDINATOR, CONF_HVAC_MODES, AvailableMode

from .const import (
    ATTR_BOOST_DURATION,
    ATTR_BOOST_TEMPERATURE,
    SERVICE_BOOST_HEATING_OFF,
    SERVICE_BOOST_HEATING_ON,
)

_LOGGER = logging.getLogger(__name__)


SUPPORT_FLAGS = 0
THERMOSTATS = 'thermostats'


hvac_mode_mapping = {
    AvailableMode.AUTO: HVAC_MODE_HEAT_COOL, 
    AvailableMode.COOL: HVAC_MODE_COOL, 
    AvailableMode.VENT: HVAC_MODE_FAN_ONLY, 
    AvailableMode.HEAT: HVAC_MODE_HEAT
}

async def async_setup_entry(hass, entry, async_add_entities):

    hub: NeoHub = hass.data[DOMAIN][HUB]
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][COORDINATOR]

    (devices_data, system_data) = coordinator.data
    thermostats = {device.name : device for device in devices_data[THERMOSTATS]}
    
    hvac_config = entry.options[CONF_HVAC_MODES] if CONF_HVAC_MODES in entry.options else {}
    _LOGGER.debug(f"hvac_config: {hvac_config}")
    for config in hvac_config:
        _LOGGER.debug(f"Overriding the default HVAC modes from {thermostats[config].available_modes} to {hvac_config[config]} for the {config} climate entity.")
        thermostats[config].available_modes = hvac_config[config]
    
    temperature_unit = system_data.CORF
    temperature_step = await hub.target_temperature_step

    entities = [NeoStatEntity(thermostat, coordinator, hub, temperature_unit, temperature_step) for thermostat in thermostats.values()]
    
    _LOGGER.info(f"Adding Thermostats: {entities}")
    async_add_entities(entities, True)

    platform = entity_platform.async_get_current_platform()
    
    platform.async_register_entity_service(
        SERVICE_BOOST_HEATING_ON,
        {
            vol.Required(ATTR_BOOST_DURATION, default=1): object,
            vol.Required(ATTR_BOOST_TEMPERATURE, default=20): int,
        },
        "set_hold",
    )

    platform.async_register_entity_service(
        SERVICE_BOOST_HEATING_OFF,
        {},
        "unset_hold",
    )



class NeoStatEntity(CoordinatorEntity, ClimateEntity):
    """ Represents a Heatmiser neoStat thermostat. """
    def __init__(self, neostat: NeoStat, coordinator: DataUpdateCoordinator, hub: NeoHub, unit_of_measurement, temperature_step):
        super().__init__(coordinator)
        _LOGGER.debug(f"Creating {neostat}")
        
        self._neostat = neostat
        self._coordinator = coordinator
        self._hub = hub
        self._unit_of_measurement = unit_of_measurement
        self._target_temperature_step = temperature_step
        self._hvac_modes = []
        if hasattr(neostat, 'standby'):
            self._hvac_modes.append(HVAC_MODE_OFF)
        for mode in neostat.available_modes:
            self._hvac_modes.append(hvac_mode_mapping[mode])
      
    @property
    def data(self):
        """Helper to get the data for the current thermostat. """
        (devices, _) = self._coordinator.data
        thermostats = {device.name : device for device in devices[THERMOSTATS]}
        return thermostats[self.name]
        
    @property
    def supported_features(self):
        """Return the list of supported features."""
        hvac_mode = self.hvac_mode
        if hvac_mode == HVAC_MODE_HEAT:
            return SUPPORT_FLAGS | SUPPORT_TARGET_TEMPERATURE
        elif hvac_mode == HVAC_MODE_COOL:
            return SUPPORT_FLAGS | SUPPORT_TARGET_TEMPERATURE
        elif hvac_mode == HVAC_MODE_OFF:
            return SUPPORT_FLAGS
        elif hvac_mode == HVAC_MODE_HEAT_COOL:
            return SUPPORT_FLAGS | SUPPORT_TARGET_TEMPERATURE_RANGE
        elif hvac_mode == HVAC_MODE_FAN_ONLY:
            return SUPPORT_FLAGS | SUPPORT_TARGET_TEMPERATURE
        else:
            _LOGGER.error(f"Unsupported hvac mode: {hvac_mode}")
            return SUPPORT_FLAGS
            
    @property
    def should_poll(self):
        """ Don't poll - we fetch the data from the hub all at once """
        return False

    @property
    def name(self):
        """ Returns the name. """
        return self._neostat.name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._neostat.name

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        if self._unit_of_measurement == "C":
            return TEMP_CELSIUS
        if self._unit_of_measurement == "F":
            return TEMP_FAHRENHEIT
        return self._unit_of_measurement
        
    @property
    def current_temperature(self):
        """ Returns the current temperature. """
        return float(self.data.temperature)

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return float(self.data.target_temperature)

    @property
    def target_temperature_high(self):
        """Return the temperature we try to reach."""
        return float(self.data.cool_temp)

    @property
    def target_temperature_low(self):
        """Return the temperature we try to reach."""
        return float(self.data.target_temperature)

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return self._target_temperature_step
         
    @property
    def extra_state_attributes(self):
        """Return the additional state attributes."""
        attributes = {}
        attributes['low_battery'] = self.data.low_battery
        attributes['offline'] = self.data.offline
        attributes['standby'] = self.data.standby
        attributes['hold_on'] = self.data.hold_on
        attributes['hold_time'] = str(self.data.hold_time)
        attributes['hold_temp'] = self.data.hold_temp
        attributes['floor_temperature'] = self.data.current_floor_temperature
        attributes['preheat_active'] = bool(self.data.preheat_active)
        return attributes
    
    @property
    def hvac_action(self):
        """Return current activity ie. currently heating, cooling, idle."""
        if self.data.heat_on:
            return CURRENT_HVAC_HEAT
        elif self.data.cool_on:
            return CURRENT_HVAC_COOL
        else:
            return CURRENT_HVAC_IDLE
            
    @property
    def hvac_mode(self):
        """Return current operation mode ie. heat, cool, off."""
        if self.data.standby or not self.data.hc_mode:
            return HVAC_MODE_OFF
            
        hc_mode = HCMode(self.data.hc_mode)
        if hc_mode == HCMode.AUTO and AvailableMode.AUTO in self.data.available_modes:
            return HVAC_MODE_HEAT_COOL
        elif hc_mode == HCMode.VENT and AvailableMode.VENT in self.data.available_modes:
            return HVAC_MODE_FAN_ONLY
        elif hc_mode == HCMode.COOLING and AvailableMode.COOL in self.data.available_modes:
            return HVAC_MODE_COOL
        else:
            return HVAC_MODE_HEAT
            
    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return self._hvac_modes
    
    @property
    def device_info(self):
        return {
            "identifiers": {("heatmiser neoStat", self._neostat.name)},
            "name": self._neostat.name,
            "manufacturer": "Heatmiser",
            "model": "neoStat",
            "suggested_area": self._neostat.name,
        }

    async def async_set_temperature(self, **kwargs):
        """ Set new target temperature. """
        _LOGGER.info(f"{self.name} : Executing set_temperature() with: {kwargs}")
        _LOGGER.debug(f"self.data: {self.data}")
        
        low_temp = kwargs.get(ATTR_TEMPERATURE) or kwargs.get(ATTR_TARGET_TEMP_LOW)
        high_temp = kwargs.get(ATTR_TARGET_TEMP_HIGH)

        set_target_temperature_task = asyncio.create_task(self._neostat.set_target_temperature(low_temp))
        response = await set_target_temperature_task
        if response:
            _LOGGER.info(f"{self.name} : Called set_target_temperature with: {low_temp} (response: {response})")
        
        set_target_cool_temperature_task = asyncio.create_task(self._neostat.set_cool_temp(high_temp))
        response = await set_target_cool_temperature_task
        if response:
            _LOGGER.info(f"{self.name} : Called set_cool_temp with: {high_temp} (response: {response})")

        # The change of target temperature may trigger a change in the current hvac_action
        # so we schedule a refresh to get new data asap.
        await self._coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set hvac mode."""
        _LOGGER.info(f"{self.name} : Executing set_hvac_mode() with: {hvac_mode}")
        _LOGGER.debug(f"self.data: {self.data}")
        
        hc_mode: HCMode = None
        if hvac_mode == HVAC_MODE_HEAT:
            hc_mode = HCMode.HEATING
        elif hvac_mode == HVAC_MODE_COOL:
            hc_mode = HCMode.COOLING
        elif hvac_mode == HVAC_MODE_HEAT_COOL:
            hc_mode = HCMode.AUTO
        elif hvac_mode == HVAC_MODE_FAN_ONLY:
            hc_mode = HCMode.VENT

        # Optimistically update the mode so that the UI feels snappy.
        # The value will be confirmed next time we get new data.
        self.data.hc_mode = hc_mode
        self.async_schedule_update_ha_state(False)

        if hc_mode:
            set_hc_mode_task = asyncio.create_task(self._neostat.set_hc_mode(hc_mode))
            response = await set_hc_mode_task
            _LOGGER.info(f"{self.name} : Called set_hc_mode() with: {hc_mode} (response: {response})")

        frost: bool = True if hvac_mode == HVAC_MODE_OFF else False
        set_frost_task = asyncio.create_task(self._neostat.set_frost(frost))
        response = await set_frost_task
        _LOGGER.info(f"{self.name} : Called set_frost() with: {frost} (response: {response})")

    async def set_hold(self, boost_duration: object, boost_temperature: int):
        """
        Sets Hold for Zone
        """
        _LOGGER.info(f"{self.name} : Executing set_hold() with duration: {boost_duration}, temperature: {boost_temperature}")
        _LOGGER.debug(f"self.data: {self.data}")

        boost_hours = 0
        boost_minutes = 0
        if str(boost_duration).count(":") > 0:
            try:
                # Try to extract hours and minutes from dict
                boost_hours = int(boost_duration['hours'])
                boost_minutes = int(boost_duration['minutes'])
                _LOGGER.debug(f"{self.name} : Duration interpreted from object")
            except:
                # Try to extract hours from string
                boost_hours, boost_minutes, _ = boost_duration.split(':')
                boost_hours = int(boost_hours)
                boost_minutes = int(boost_minutes)
                _LOGGER.debug(f"{self.name} : Duration interpreted from string")
        else:
            boost_hours = int(boost_duration)
            _LOGGER.debug(f"{self.name} : Duration interpreted from number")
            

        if boost_minutes > 59:
            _boost_revised_minutes = boost_minutes % 60
            boost_hours += int((boost_minutes - _boost_revised_minutes) / 60)
            boost_minutes = _boost_revised_minutes
        if boost_hours > 99:
            boost_hours = 99

        message = {"HOLD": [{"temp":boost_temperature, "hours":boost_hours, "minutes":boost_minutes, "id":self.name}, [self.name]]}
        reply = {"result": "temperature on hold"}

        result = await self._hub._send(message, reply)

        # Optimistically update the mode so that the UI feels snappy.
        # The value will be confirmed next time we get new data.
        
        self.data.hold_on = True
        self.data.hold_time = str(f"{boost_hours}:{boost_minutes}:00")
        self.data.hold_temp = int(boost_temperature)
        self.async_schedule_update_ha_state(False)

        return result


    async def unset_hold(self):
        """
        Unsets Hold for Zone
        """

        message = {"HOLD": [{"temp":20, "hours":0, "minutes":0, "id":self.name}, [self.name]]}
        reply = {"result": "temperature on hold"}

        result = await self._hub._send(message, reply)
        
        # Optimistically update the mode so that the UI feels snappy.
        # The value will be confirmed next time we get new data.
        
        self.data.hold_on = False
        self.data.hold_time = str("0:00:00")
        self.data.hold_temp = 20
        self.async_schedule_update_ha_state(False)

        return result