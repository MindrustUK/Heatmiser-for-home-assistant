# Change Log

## 20251211

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/321 by @patch0, add support for NeoHub V3
- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/320 by @patch0, add support for NeoStat V3

## 20251119

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/311 by @ocrease, Use standard HA remove device option and automatically add new devices
- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/312 by @ocrease, type checking code cleanup
- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/313 by @ocrease, clean up devices removed from hub while Home Assistant is down

## 20251118

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/310 by @ocrease, improve device removal flow

## 20251117

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/309 by @ocrease, add support for adding/removing devices

## 20251113

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/308 by @ocrease, support setting custom min/max temperatures - see https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/302

## 20251112

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/303 by @ocrease, fix issue with timer profiles where some days are empty
- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/305 by @ocrease, make sure api token is redacted in diagnostics

## 20251104

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/299 by @ocrease, add support for NeoStat Touch

## 20251103

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/297 by @ocrease, add support for NeoStat Pro

## 20250731

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/295 by @ocrease, raise issue and offer fix when old device entries are detected

## 20250726

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/293 by @ocrease, remove backwards compatibility code for HVAC Mode

## 20250725

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/292 by @ocrease, workaround for non unique serial numbers

## 20250425

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/287 by @ocrease, handle case when engineers data is not reported by the hub

## 20250425

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/286 by @ocrease, improve robustness of diagnostics

## 20250418

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/282 by @ocrease, skip set_hvac_mode if already set to requested value

## 20250310

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/277 by @ocrease, check host is not already configured. Also documentation updates for Discovery

## 20250309

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/273 by @ocrease, implement discovery and connection using connect button. Stop using fake serial number, use mac address instead
- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/274 by @ocrease, fix config flow error for hubseek discovery
- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/275 by @ocrease, use mac address from web socket connection if not already retrieved via discovery
- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/276 by @ocrease, add connect button connection option for discovered devices

## 20250303

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/272 by @ocrease, fix for Zeroconf discovery

## 20250301

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/270 by @ocrease, implement discovery using udp broadcast on port 19790

## 20250225

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/268 by @ocrease, use NeoHubAPI 2.8 to benefit from improved connection handling

## 20250224

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/266 by @ocrease, handle invalid/disabled profile times

## 20250223

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/263 by @ocrease, fix Invalid Json error when setting temperature using WebSocket API

## 20250223

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/261 by @ocrease, pre-release cleanup tasks

## 20250222

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/260 by @mr-miles, added websocket support

## 20250208

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/258 by @ocrease, Standby is now a preset rather than HVACMode.OFF

## 20250206

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/257 by @ocrease, fixed ZeroconfServiceInfo deprecation warning

## 20250201

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/254 by @ocrease, improved options configuration flow

## 20250129

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/253 by @ocrease, added lock and user limit

## 20250129

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/251 by @ocrease, fixes issues with HVAC Mode configuration for NeoStat HC

## 20250126

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/248 by @ocrease, adds upsert mode to profile services.

## 20250124

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/247 by @ocrease, Improves NeoStatHC compatibility.

## 20250120

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/243 by @ocrease, changes to Zeroconf and Optimum start times.
- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/246 by @ocrease, Adds service for programming thermostats.

## 20250116

- Major release, version 3.0.0 now available. Massive thanks to @ocrease. This is a huge release, Please see previous notes for all changes.

## 20241230

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/235 by @ocrease, beta 13 fixes.

## 20241227

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/232 by @ocrease, documentation update.

## 20241224

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/231 by @ocrease, documentation improvements.

## 20241220

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/230 by @ocrease, combines away sensors, tweaks repeater button.

## 20241219

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/227 by @ocrease, adds service for holiday/away mode control.
- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/228 by @ocrease, fixes naming of remove button.
- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/229 by @ocrease, Add documentation using GitHub pages.

## 20241218

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/226 by @ocrease, fixes profile issues in beta9

## 20241217

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/225 by @ocrease, addresses issues with profiles not being available and other bugs in beta8.

## 20241212

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/224 by @ocrease, Bumps NeoHub API version and fixes issues in beta7.

## 20241212

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/223 by @ocrease, Bumps NeoHub API version and adds support for repeater and profile features.

## 20241206

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/221 by @ocrease, adds Time / NTP fixes and hub features.
- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/222 by @ocrease, adds flag for modified temperatures.

## 20241129

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/220 by @ocrease, fixes for thermostat operation when in standby.

## 20241118

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/219 by @ocrease, Additional floor related parameters.

## 20241115

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/207 by @ocrease, improves away mode.

## 20241113

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/218 by @ocrease, improves icons.

## 20241111

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/213 by @ocrease, improves overall quality.
- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/214 by @ocrease, fixing sensor type.
- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/216 by @ocrease, improves robustness when devices are no longer available.

## 20241105

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/212 by @ocrease, should address NeoStat V1 in timeclock mode behaviours with Standby mode.
- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/211 by @ocrease, adds automation and improves consistency of release versions.

## 20241031

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/201 by @ocrease. I would suggest to treat this as a complete re-write. The change list is huge and includes many fixes and new features. I recommend reading the PR for details.

## 20241030

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/203 - Improves diagnostics, thanks ocrease.
- Updated readme (Supporting this project).
- Forked default branch Version 1.6

## 20241029

- Move Dev branch installation notes from readme.md to dev_installation.md

## 20241028

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/200 - Adds diagnostics, thanks @ocrease.

## 20241024

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/191 - Should cleanup dev branch.

## 20241023

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/190 - Should improve hold behaviour.

## 20241022

- Merged https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/187 should re-introduce version 1 style hold behaviour for timers.

## 20241021

- Updating README.md with improved troubleshooting steps.

## 20241020

- Change hold service behaviour for: https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/185

## 20241018

- Bumped dependency on neohubapi to 2.2, hopefully addresses wireless sensor behavior and repeaters in issue: https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/176

## 20241016

- Version 1.5 Release to Main
  - Current Main branch archived to branch Version 1.0
  - Version 1.5 is a fork of the dev branch with the additional hold controls removed. This has been done as the main
    branch is stale and prompting lots of reports for things fixed up stream that haven't made it to main yet. This should
    satisfy many requirements reported or requested recently.
  - Known issues: Heatmiser Neo Plug functionality is broken. I've made the call that the benefits of getting this
    released even with the missing functionality outweighs the missing element. For anyone who desperately needs support
    for the Neo Plug, please use the Version 1.0 branch. This is the top thing on my list to fix at present.

## 20241013

- Allow calling hold service with float temperatures: https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/175

## 20241003

- Fixes following previous work to avoid entities being added twice when multiple instances of the integration are in use.

## 20240928

- Multiple fixes and enhancements relating to issue: https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/170 - Multiple Hubs / Instances should now work.
- **Breaking changes:** Unique IDs are now generated based on serial number, this will cause duplicate entries and a bunch of breakage. Please remove and re-add the integration to clear any issues with this.
- Added support for device serial numbers to ensure device ID's are more distinct when multiple hubs and instances of the integration are in use.
- Serial numbers now report in device info.
- Heatmiser NeoHub now appears as a device. The Serial Number is a placeholder for now. Longer term I'll make this configurable or hopefully Heatmiser will add some API support.
- Heatmiser NeoHub does not have a 'real' serial number, issue raised with Heatmiser here: https://dev.heatmiser.com/t/no-method-to-retrive-serial-nubmer-for-neohub-in-api/1298
- Added Heatmiser NeoHub types / models to constants.
- Report Heatmiser NeoHub type / model in device info.
- Relationships between Heatmiser devices and the Hub now work (via_device).

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
- Reflect correct firmware, model, manufacturer etc. in device info (Thermostats etc. Hub information to follow).
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
- Added Input for Hold Hours and Minutes
- Added Hold State Switches (IE hold on or hold off)
- Added Hold Temperature, or Hold by Time depending on Thermostat or TimeClocks / Neoplugs.
- More stuff I forgot and will add later.

## 20231219

- Added HeatmiserNeoTimerOutputActiveSensor to sensors.
