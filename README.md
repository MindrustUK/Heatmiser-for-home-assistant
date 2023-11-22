<!-- SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
-->

# Dev Branch
Please note you are browsing a heavy work in progress branch. Many things will probably be broken and this readme will change frequently. Please pay close attention to commits to really understand what's happening. Please use the master branch unless you are brave or intentionally testing 'completed' functions to report bugs.

# Heatmiser-for-home-assistant

An integration for [Home Assistant](https://www.home-assistant.io/) to add support for [Heatmiser's Neo-Hub and 'Neo'](https://www.heatmiser.com/en/heatmiser-neo-overview/) range of products.

This is a work in progress for adding Heatmiser Neo-hub support to Home Assistant (https://home-assistant.io/), I maintain this as a weekend project only so don't expect fast updates but feel free to raise issues as needed.

# Announcements

This is a major new branch, Many things broken, change log as follows:

## Change log
[Change Log](https://github.com/MindrustUK/Heatmiser-for-home-assistant/blob/dev/changelog.md)

# Known issues - Read me first!
Heatmiser have labeled the primary API used by this integration as "Legacy API". Please note if your integration stops working, or doesn't work on initial installation, please check the phone app and enable "Legacy API" support.

Support for adding Token based authentication is present in the underlying noehubapi and will be coming to this plugin natively at a future date.

Please also note that the NeoStat WiFi does not have an API, and so cannot be used with this (or any) NeoHub-based integration.

# Installation:

Before starting installation you should know the IP address of the Neo-hub. If you don't know the IP address, use one of the approaches suggested below to find your neo-hubs IP address.

It is suggested that you should allocate a static IP to the Heatmiser Neo-hub or use a DNS entry that's resolvable by Home-Assistant (see notes below).

The preferred method of installation is using HACS although the legacy, cut-and-paste method of installation can still be used and is described under Options below. Installing via HACS is a two-stage process. Firstly, add the Heatmiser repository to HACS, then secondly adding the Heatmiser Integration to Home Assistant.

HACS is available from https://github.com/hacs and there are copious resorces available (e.g. http://hacs.xyz) about its installation. This will involve lots of Home Assisant restarts! Once you have HACS running...

## Dev branch only

If you wish to install the development version of the code from the Dev branch please follow the instructions below. If not please continue to Stage 1.

For Hass.io:
Install and configure SSH server from the "Add-on store". Once you have shell run the following:
```
mkdir -p /config/custom_components
cd /tmp/
git clone -b dev https://github.com/MindrustUK/Heatmiser-for-home-assistant /tmp/heatmiserneo
mv /tmp/heatmiserneo/custom_components/heatmiserneo /config/custom_components/
rm -rf /tmp/heatmiserneo/
```
Now restart your Home Assistant installation and the development verison of the plugin should load.

## Stage 1: Add to HACS

Open HACS and go to the Settings tab

![CustomIntegration](https://github.com/PhillyGilly/Heatmiser-for-home-assistant/blob/master/%231.png)

Add "https://github.com/MindrustUK/Heatmiser-for-home-assistant" as a repository as an "Integration" type, note you need to include the quote marks around the repository name.
Go to the Integrations tab
Search for "Heatmiser Neo Integration", (it will probably be at the bottom!) select and install

![CustomRepositories](https://github.com/PhillyGilly/Heatmiser-for-home-assistant/blob/master/%232.png)

When this message appears follow it by going to Configuraton -> Server Tools and then "Restart"
![RestartNotice](https://github.com/PhillyGilly/Heatmiser-for-home-assistant/blob/master/%233.png)

## Stage 2: Configure the integration in HA:

Go to Configuration -> Integrations and click on the orange icon in the bottom right corner produces a drop down list and scroll down to "Heatmiser Neo Climate".

![HowToIntegrate](https://github.com/PhillyGilly/Heatmiser-for-home-assistant/blob/master/%234.png)

When the integration starts you may need to enter the Neo-hub IP address. The port is always 4242.

![Config](https://user-images.githubusercontent.com/56273663/98438427-fb40f200-20e1-11eb-8437-a0288548082b.png)

If you are successful, after restarting HA you will see the results under Configuration -> Entities 

![Entities](https://github.com/PhillyGilly/Heatmiser-for-home-assistant/blob/master/%235.png)

# Note on finding your heatmiser neohub

Suggestions from Haakon Storm Heen, Use namp on your local network range:

```nmap -Pn -p4242 -oG - 192.168.1.0/24 | grep 4242 | grep -i open```

Where supported by your network and machine you can use a tool such as ZeroConfServiceBrowser or "Discovery - DNS-SD Browser" (iPhone) to detect the mDNS broadcast from the hub.  Look for "_hap._tcp." and the "Heatmiser neoHub" should be listed as a device.

Note: If you discover the device via mdns/zeroconf then you can use the hostname advertised by the service.

# (Optional) Legacy Installation:

For Hass.io:
Install and configure SSH server from the "Add-on store". Once you have shell run the following:
```
cd /config/
mkdir custom_components
cd /config/custom_components
git clone https://github.com/MindrustUK/Heatmiser-for-home-assistant /tmp/heatmiserneo
mv /tmp/heatmiserneo/custom_components/heatmiserneo .
```

For Windows 10 Manual installation:
Install and configure Samba Share from the "Add-on store". Change directory to config location then run the following:
```
Create a network drive pointing at your Home Assistant config directory.
If there is not a sub-directory in this drive called custom_components create it.
Now create a subdirectory under custom_components called heatmiserneo.
Download all the files from the Heatmiser-for-home-assistant Github repository.
Copy and paste all thoese files into the new Home Assistant heatmiserneo sub-directory.
```

# Services
This integration provides two services that can be called from home assistant.

## Hold
You can apply a hold using the `heatmiserneo.hold_on` service.  This can be used to target an entity, device or area and also accepts the following parameters:
- `hold_duration` - how long to hold the specified temperature.  This is given in Home Assistant duration format (hh:mm e.g. `hold_duration: 01:30`) and can go up to 99:59.
- `hold_temperature` - sets the temperature to hold.  Specified as an integer (e.g. `hold_temperature: 20`).

If there is an existing hold on any device targeted by the service call, it is replaced by the new hold.
## Release Hold
You can release any existing hold on a NeoStat specified by entity, device or area.  There are no other parameters.

## Related Attributes
NeoStat climate entities reads the following attributes that are relevant to the Hold functionality:
- `hold_on`: whether a hold is in action
- `hold_temperature`: what temperature is being held (note that this will have a numeric value, even if there is no hold in effect - this is a function of the NeoStat, not of the integration)
- `hold_duration`: shows how many hours:minutes are remaining on the hold.  If no hold is active, shows '0:00'.
