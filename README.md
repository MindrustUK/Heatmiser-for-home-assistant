<!-- SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
-->

# Heatmiser-for-home-assistant
Heatmiser Neo-Hub / Neostat / Neostat-e support for home-assistant.io

This is a work in progress for adding Heatmiser Neo-hub support to Home Assistant (https://home-assistant.io/), I maintain this as a weekend project only so don't expect fast updates but feel free to raise issues as needed.

# Known issues - Read me first!
For some reason Heatmiser have labeled the API used by this intergration as "Legacy API". Please note if your intergration stops working, or doesn't work on initial installation, please check the phone app and enable "Legacy API" support.

# Installation:

Before starting installation you should know the IP address of the Neo-hub. If you don't know the IP address, use one of the approaches suggested below to find your neo-hubs IP address.

It is suggested that you should allocate a static IP to the Heatmiser Neo-hub or use a DNS entry that's resolvable by Home-Assistant (see notes below).

The preferred method of installation is using HACS although the legacy, cut-and-paste method of installation can still be used and is described under Options below. Installing via HACS is a two-stage process. Firstly, add the Heatmiser repository to HACS, then secondly adding the Heatmiser Integration to Home Assistant.

HACS is available from https://github.com/hacs and there are copious resorces available (e.g. http://hacs.xyz) about its installation. This will involve lots of Home Assisant restarts! Once you have HACS running...

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
mv /tmp/heatmiserneo/custom-components/heatmiserneo .
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

Now follow instructions above.
