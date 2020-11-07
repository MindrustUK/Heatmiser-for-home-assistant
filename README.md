# Heatmiser-for-home-assistant
Heatmiser Neo-Hub / Neostat / Neostat-e support for home-assistant.io

This is a work in progress for adding Heatmiser Neo-hub support to Home Assistant (https://home-assistant.io/), I maintain this as a weekend project only so don't expect fast updates but feel free to raise issues as needed.

Installation:

Before starting instalation you should know the IP address of the Neo-hub. If you don't know the IP address, use one of the approaches suggested below to find your neo-hubs IP address.

It is suggested that you should allocate a static IP to the Heatmiser Neo-hub or use a DNS entry that's resolvable by Home-Assistant.

The preferred method of installation is to use the Home Assistant function which you access via Configuration->Integrations.
Clicking on the orange icon in the bottom right corner produces a drop down list and scroll down to "Heatmiser Neo Climate".
![HowToIntegrate](https://user-images.githubusercontent.com/56273663/98438130-07c44b00-20e0-11eb-8895-166cb856643a.png)

When the integration starts you will need to enter the Neo-hub IP address. The port is always 4242.
![Config](https://user-images.githubusercontent.com/56273663/98438427-fb40f200-20e1-11eb-8437-a0288548082b.png)

When the integration is running you can still change logger options by editing (usually) configuration.yaml as described below.



Legacy installation:

You can also install manually if you are running a version of HA that doesn't offer Integrations as below.
Install and configure SSH server from the "Add-on store". Once you have shell run the following:
```
cd /config/
mkdir custom_components
cd /config/custom_components
git clone https://github.com/MindrustUK/Heatmiser-for-home-assistant
mv Heatmiser-for-home-assistant heatmiserneo
```

For Manual / Custom installations:
Change directory to config location then run the following:
```
mkdir custom_components
cd /config/custom_components
git clone https://github.com/MindrustUK/Heatmiser-for-home-assistant
mv Heatmiser-for-home-assistant heatmiserneo
```
For both above scenarios then complete configuration as follows:

General Configuration:

[Authors note: Add notes about how to find your heatmiser neohub on your network (Nmap, checking your routers DHCP table, ARP etc).]

Suggestions from Haakon Storm Heen, Use namp on your local network range:

```nmap -Pn -p4242 -oG - 192.168.1.0/24 | grep 4242 | grep -i open```

Heatmiser Neo integration can be setup via Home Assistant Integrations page.

(Optional) Logging Configuration:

If debugging is required (submitting bug reports etc.) logger verbosity can be adjusted as follows:

```yaml
logger:
  default: warning
  logs:
    custom_components.heatmiserneo: debug
```
