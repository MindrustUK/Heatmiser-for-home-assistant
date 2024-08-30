# Change Log

## 20240830
- Better handling of invalid temperatures on hub disconnect as per: https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/155
- Added switch to control standby on timers as per: https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/153

## 20240828
- Fix deprecation notice: https://developers.home-assistant.io/blog/2024/06/12/async_forward_entry_setups/
- Handling of 127 and 255 temperatures on hub disconnect as per: https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/155
- Fix in button.py for Model ID as per: https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/159
- Fixed HVAC OFF mode for: https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/157 also improves features per device type. I.e. enable cooling for stats that support it. 

## 20231121
- Added support for Temperature Sensors
- Added Support for Window Door Contact Sensors
- Reflect correct firmware, model, manufacturer etc. in device info (Thermostats etc. Hub information to folllow).
- Patched behavior of Neostat V1 to only allow for heating due to API bug in Heatmiser Neo Hub.
- Added Battery attribute to devices that are battery powered.
- Reflect battery sensor for battery low in any 'battery powered' device.
- Refactored "device offline" sensor.
- Remapped HVAC action and HVAC modes values to better align with home-assistant intentions.
- Refactor Offline sensor from BinarySensorDeviceClass.PROBLEM to BinarySensorDeviceClass.CONNECTIVITY. See: https://developers.home-assistant.io/docs/core/entity/binary-sensor/
- Refactor Battery sensor BinarySensorDeviceClass.BATTERY. See: https://developers.home-assistant.io/docs/core/entity/binary-sensor/
- Use device_id as unique identifier for all Heatmiser Neo Devices in device registry.
- Flattened all Heatmiser Neo Devices into a single neo_device simple-namespace and class.
- Added time_clock_mode to neo_device class where device_type is thermostat ie 1 - NeoStat , 12 - NeoStat V2
- Added offline handling for all Heatmiser Neo Devices and surfaced this to Home Assistant.
- Fixed hvac_mode vs hvac_action.
- Added Identify button
- Added Hold Active sensors
- Added Input for Hold Hours and Mintues
- Added Hold State Switches (IE hold on or hold off)
- Added Hold Temperature, or Hold by Time depending on Thermostat or TimeClocks / Neoplugs.
- More stuff I forgot and will add later.

## 20231219
- Added HeatmiserNeoTimerOutputActiveSensor to sensors.
