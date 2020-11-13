# Heatmiser-for-home-assistant
Heatmiser Neo-Hub / Neostat / Neostat-e support for home-assistant.io

This is a work in progress for adding Heatmiser Neo-hub support to Home Assistant (https://home-assistant.io/), I maintain this as a weekend project only so don't expect fast updates but feel free to raise issues as needed.

# Installation:

Before starting instalation you should know the IP address of the Neo-hub. If you don't know the IP address, use one of the approaches suggested below to find your neo-hubs IP address.

It is suggested that you should allocate a static IP to the Heatmiser Neo-hub or use a DNS entry that's resolvable by Home-Assistant.

## Step 1: Copy the component code to home assistant installation

Download or clone the code from this repository and copy to home assistant installation under `/config/custom_components/heatmiserneo`

This can be done via the Samba Add-on or by SSH/Terminal. 
Install and configure SSH server from the "Add-on store". Once you have shell run the following:
```
cd /config/
mkdir custom_components
cd /config/custom_components
git clone https://github.com/MindrustUK/Heatmiser-for-home-assistant
mv Heatmiser-for-home-assistant heatmiserneo
```

## Step 2: Restart Home Assistant
Go to Configuraton -> Server Tools and then "Restart"

## Step 2: Configure the integration via the integrations menu:

Clicking on the orange icon in the bottom right corner produces a drop down list and scroll down to "Heatmiser Neo Climate".
![HowToIntegrate](https://user-images.githubusercontent.com/56273663/98438130-07c44b00-20e0-11eb-8895-166cb856643a.png)

When the integration starts you will need to enter the Neo-hub IP address. The port is always 4242.
![Config](https://user-images.githubusercontent.com/56273663/98438427-fb40f200-20e1-11eb-8437-a0288548082b.png)

# Note on finding your heatmiser neohub

Suggestions from Haakon Storm Heen, Use namp on your local network range:

```nmap -Pn -p4242 -oG - 192.168.1.0/24 | grep 4242 | grep -i open```

Where supported by your network and machine you can use a tool such as ZeroConfServiceBrowser or "Discovery - DNS-SD Browser" (iPhone) to detect the mDNS broadcast from the hub.  Look for "_hap._tcp." and the "Heatmiser neoHub" should be listed as a device.

Note: If you discover the device via mdns/zeroconf then you can use the hostname advertised by the service.

# (Optional) Logging Configuration:

If debugging is required (submitting bug reports etc.) logger verbosity can be adjusted as follows:

```yaml
logger:
  default: warning
  logs:
    custom_components.heatmiserneo: debug
```
