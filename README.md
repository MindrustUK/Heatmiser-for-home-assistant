<!-- SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
-->

# Heatmiser-for-home-assistant

An integration for [Home Assistant](https://www.home-assistant.io/) to add support for [Heatmiser's Neo-Hub and 'Neo'](https://www.heatmiser.com/en/heatmiser-neo-overview/) range of products.

This is a work in progress for adding Heatmiser Neo-hub support to Home Assistant (https://home-assistant.io/), I maintain this as a weekend project only so don't expect fast updates but feel free to raise issues as needed.

# Announcements

Branch Version 1.5 now promoted to main, please see _Change Log_ below for further info

## Change log
[Change Log](https://github.com/MindrustUK/Heatmiser-for-home-assistant/blob/Version_1.5/docs/changelog.md)

# Known issues - Read me first!
- Heatmiser have labeled the primary API used by this integration as "Legacy API". Please see [Troubleshooting](#troubleshooting) for further details.
- Support for adding Token based authentication is present in the underlying noehubapi and will be coming to this plugin natively at a future date.
- Note specifically the NeoStat WiFi device does not have an API, and so cannot be used with this (or any) NeoHub-based integration.
- Neoplug devices are broken in the dev and 1.5 branch and are due to be fixed as soon as I get a chance to look into the details.

# Installation:

Before starting installation you should know the IP address of the Neo-hub. If you don't know the IP address, use one of the approaches suggested below to find your neo-hubs IP address.

It is suggested that you should allocate a static IP to the Heatmiser Neo-hub or use a DNS entry that's resolvable by Home-Assistant (see notes below).

The preferred method of installation is using HACS although the legacy, cut-and-paste method of installation can still be used and is described under Options below. Installing via HACS is a two-stage process. Firstly, add the Heatmiser repository to HACS, then secondly adding the Heatmiser Integration to Home Assistant.

HACS is available from https://github.com/hacs and there are copious resources available (e.g. http://hacs.xyz) about its installation. This will involve lots of Home Assistant restarts! Once you have HACS running...

## Stage 1: Add to HACS

Open HACS and go to the Settings tab

![CustomIntegration](https://github.com/PhillyGilly/Heatmiser-for-home-assistant/blob/master/%231.png)

Add "https://github.com/MindrustUK/Heatmiser-for-home-assistant" as a repository as an "Integration" type, note you need to include the quote marks around the repository name.
Go to the Integrations tab
Search for "Heatmiser Neo Integration", (it will probably be at the bottom!) select and install

![CustomRepositories](https://github.com/PhillyGilly/Heatmiser-for-home-assistant/blob/master/%232.png)

When this message appears follow it by going to Configuration -> Server Tools and then "Restart"
![RestartNotice](https://github.com/PhillyGilly/Heatmiser-for-home-assistant/blob/master/%233.png)

## Stage 2: Configure the integration in HA:

Go to Configuration -> Integrations and click on the orange icon in the bottom right corner produces a drop down list and scroll down to "Heatmiser Neo Climate".

![HowToIntegrate](https://github.com/PhillyGilly/Heatmiser-for-home-assistant/blob/master/%234.png)

When the integration starts you may need to enter the Neo-hub IP address. The port is always 4242.

![Config](https://user-images.githubusercontent.com/56273663/98438427-fb40f200-20e1-11eb-8437-a0288548082b.png)

If you are successful, after restarting HA you will see the results under Configuration -> Entities 

![Entities](https://github.com/PhillyGilly/Heatmiser-for-home-assistant/blob/master/%235.png)

# (Optional) Legacy Installation:

## For Hass.io:
Install and configure SSH server from the "Add-on store". Once you have shell run the following:
```
mkdir -p /config/custom_components
cd /tmp/
git clone https://github.com/MindrustUK/Heatmiser-for-home-assistant /tmp/heatmiserneo
mv /tmp/heatmiserneo/custom_components/heatmiserneo /config/custom_components/
rm -rf /tmp/heatmiserneo/
```

Restart Home Assistant and setup the integration.

## For Windows 10 Manual installation:
Install and configure Samba Share from the "Add-on store". Change directory to config location then run the following:
```
Create a network drive pointing at your Home Assistant config directory.
If there is not a sub-directory in this drive called custom_components create it.
Now create a subdirectory under custom_components called heatmiserneo.
Download all the files from the Heatmiser-for-home-assistant Github repository.
Copy and paste all thoese files into the new Home Assistant heatmiserneo sub-directory.
```

# Troubleshooting

## I can't find my Neohub

### Try discovery using nmap

As suggested by Haakon Storm Heen, try namp on your local network range:

```nmap -Pn -p4242 -oG - 192.168.1.0/24 | grep 4242 | grep -i open```

Where supported by your network and machine you can use a tool such as ZeroConfServiceBrowser or "Discovery - DNS-SD 
Browser" (iPhone) to detect the mDNS broadcast from the hub.  Look for "_hap._tcp." and the "Heatmiser neoHub" should be
listed as a device.

Note: If you discover the device via mdns/zeroconf then you can use the hostname advertised by the service.

### Using Heatmiser Discovery

Note: This will eventually be part of the setup process and done internally.

- Start a listener in a terminal: ```nc -ulk -p 19790```
- Issue the discovery command ```echo -n "hubseek" | nc -b -u 255.255.255.255 19790```

A response such as ```hubseek{"ip":"192.168.0.2","device_id":"nn:nn:nn:nn:nn:nn"}``` should then be rendered in the 
listening terminal.

## I can't connect to my Neohub

- If you are not using token based authentication;
  - Check the Heatmiser Mobile App and under _SETTINGS_ -> _API_ -> _API TOKENS_ ensure that _Legacy API_ is enabled.

  - After checking the above please try testing with the hub using the following commands from the Home Assistant 
  terminal (Provided by the addon "Terminal & SSH");
  - ```printf '{"INFO":0}\0' | nc YOUR_DEVICE_IP_HERE 4242```

- If you are trying to authenticate using token based authentication;
  - The following instructions are a placeholder for now and will be further expanded on once the integration better 
  - supports token based authentication via web sockets.
  - Ensure you are applying this configuration to a Heatmiser NeoHub 2 or later. The Version 1 Hub does not support this 
  authentication mechanism.
  - Ensure that your token is correct, this can be checked in the Heatmiser mobile app under _SETTINGS_ -> _API_ ->
  _API TOKENS_
  - Use postman to troubleshoot.

### The info command times out
- Have you tried to ping the neohub? ```ping IP_ADDRESSS_HERE``` if this fails the Neohub is likely unreachable for some 
reason.

## Other common troubleshooting steps to try

- Try restarting Home Assistant.
- Check the logs: Within Home Assistant, from the _Settings_ menu navigate to _Logs_ and look for anything relating to 
_Heatmiser_.
- Enable debugging and check the logs again:
  - Within Home Assistant, from the _Settings_ menu navigate to _Devices & Services_ and then to  
  _Heatmiser Neo Climate_ and from the left side menu select _Enable debug logging_.
  - Now navigate to _Developer Tools_ and then to _RESTART_, when prompted select _Restart Home Assistant_ follow the 
  steps above to check the logs again.
- Remove the existing installation and re-install: To ensure total removal of the _Heatmiser Neo Climate_ integration 
using Home Assistant terminal (Provided by the addon "Terminal & SSH") issue the following command; 
```rm -rf /config/custom_components/heatmiserneo``` restart Home Assistant and install from fresh.

## Bug Reporting and asking for help:
- Please ensure that if you wish to report a bug that is not fixed in the [Dev Branch](https://github.com/MindrustUK/Heatmiser-for-home-assistant/tree/dev) before submitting your bug.
- Include logs, versions, any troubleshooting attempted, outputs and expected vs observed behaviour. 
- Please note "It doesn't work" and other vague "It's broken" messages will only prompt a lot of questions to understand 
why things are broken, the more information upfront will help expedite any advice and resolution.

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

# Supporting this project
As per: [https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/133](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/133) a few users found this useful and wanted to support my work. I'm very grateful and humbled, thanks for the show of support! As such I've setup the following to accept donations to support my work;

[https://ko-fi.com/MindrustUK](https://ko-fi.com/MindrustUK)

[https://liberapay.com/MindrustUK](https://liberapay.com/MindrustUK)

If anyone from Heatmiser is reading; some more devices to build out a more complete hardware test suite to ensure coverage would really help the project. Feel free to reach out if you want to help with this.

This is not a completely solo project and credit is due to anyone who contributed. Please see the github commits to support these awesome devs if there was some work that helped you. I'd particularly like to call out Andrius Štikonas for migrating the original calls to a Home Assistant compatible library, please also consider supporting their efforts via: [https://gitlab.com/neohubapi/neohubapi/](https://gitlab.com/neohubapi/neohubapi/) or [https://stikonas.eu/](https://stikonas.eu/)
