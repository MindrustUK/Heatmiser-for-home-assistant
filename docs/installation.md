---
title: Installation
nav_order: 2
---

# Installation:

Before starting installation you should know the IP address of the Neo-hub. If you don't know the IP address, use one of the approaches suggested below to find your neo-hubs IP address.

It is suggested that you should allocate a static IP to the Heatmiser Neo-hub or use a DNS entry that's resolvable by Home-Assistant (see notes below).

The preferred method of installation is using HACS although the legacy, cut-and-paste method of installation can still be used and is described under Options below. Installing via HACS is a two-stage process. Firstly, add the Heatmiser repository to HACS, then secondly adding the Heatmiser Integration to Home Assistant.

HACS is available from [here](https://github.com/hacs) and there are copious resources available (e.g. [HACS XYZ](http://hacs.xyz)) about its installation. This will involve lots of Home Assistant restarts! Once you have HACS running...

## Stage 1: Add to HACS

Open HACS and go to the Settings tab

![CustomIntegration](/images/installation_1.png)

Add "https://github.com/MindrustUK/Heatmiser-for-home-assistant" as a repository as an "Integration" type, note you need to include the quote marks around the repository name.
Go to the Integrations tab
Search for "Heatmiser Neo Integration", (it will probably be at the bottom!) select and install

![CustomRepositories](/images/installation_2.png)

When this message appears follow it by going to Configuration -> Server Tools and then "Restart"
![RestartNotice](/images/installation_3.png)

## Stage 2: Configure the integration in HA:

Go to Configuration -> Integrations and click on the orange icon in the bottom right corner produces a drop down list and scroll down to "Heatmiser Neo Climate".

![HowToIntegrate](/images/installation_4.png)

You will have the option of how to discover the hub

![DiscoveryOptions](/images/installation_5_discovery.png)

- Connect Button - Select this option to connect to the hub by pressing the Connect button on the hub within 2 minutes
- Hub Discovery - Select this option to attempt to discover any hubs on your network
- Manual - Select this option to set up the hub with its ip address or hostname

Using Connect Button, the hub connection will be established automatically using the Websocket API if available (not available on older Hub firmwares) or the Legacy API. With the other two options (discovery or manual), you will have to select which connection method you want to use.

![ConnectionOptions](/images/installation_5_menu.png)

### WebSocket API

You will need to obtain an API Key from the Heatmiser App (Settings -> API). The port is always 4243 for the Websocket API

![Websocket API](/images/installation_5_websocket.png)

### Legacy API

You will need to enable the legacy API in the Heatmiser App (Settings -> API). The port is always 4242 for the Legacy API

![Config](/images/installation_5.png)

If you are successful, you will see that the hub has been added and you should be able to see the devices.

![Entities](/images/installation_6.png)

# (Optional) Pre-relase Installation:

You can use the `Redownload` functionality in HACS to chose a prerelease version if you want to try the latest development features.

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
Copy and paste all those files into the new Home Assistant heatmiserneo sub-directory.
```
