---
title: FAQs
nav_order: 10
---

# Troubleshooting

## Automated discovery issues

Automated discovery works using UPD broadcasts. If your Hub is on a different subnet/network to Home Assistant, this
integration will not detect your hub unless your router unless the UDP broadcasts are specifically forwarded/relayed
from the Hub subnet to the Home Assistant subnet. Details for each method are below:

### Connect Button

Hub discovery and auto connect using the connect button on the hub relies on UDP broadcasts from the hub on UDP port 1979

### Heatmiser Discovery (eg hubseek)

Heatmiser discovery relies on UDP broadcasts from the hub on UDP port 19790

### Zeroconf/MDNS

Zeroconf/MDNS discovery works on UDP port 5353

## I can't find my Neohub

### Try discovery using nmap

As suggested by Haakon Storm Heen, try namp on your local network range:

`nmap -Pn -p4242 -oG - 192.168.1.0/24 | grep 4242 | grep -i open`

Where supported by your network and machine you can use a tool such as ZeroConfServiceBrowser or "Discovery - DNS-SD
Browser" (iPhone) to detect the mDNS broadcast from the hub. Look for "\_hap.\_tcp." and the "Heatmiser neoHub" should be
listed as a device.

Note: If you discover the device via mdns/zeroconf then you can use the hostname advertised by the service.

### Using Heatmiser Discovery

- Start a listener in a terminal: `nc -ulk -p 19790`
- Issue the discovery command `echo -n "hubseek" | nc -b -u 255.255.255.255 19790`

A response such as `hubseek{"ip":"192.168.0.2","device_id":"nn:nn:nn:nn:nn:nn"}` should then be rendered in the
listening terminal.

## I can't connect to my Neohub

- If you are using the "Connect Button" method and your hub is on a different subnet, make sure UDP broadcasts on port 1979 are forwarded to the Home Assistant subnet.

- If you are not using token based authentication;
  - Check the Heatmiser Mobile App and under _SETTINGS_ -> _API_ -> _API TOKENS_ ensure that _Legacy API_ is enabled.

  - After checking the above please try testing with the hub using the following commands from the Home Assistant
    terminal (Provided by the addon "Terminal & SSH");
  - `printf '{"INFO":0}\0' | nc YOUR_DEVICE_IP_HERE 4242`

- If you are trying to authenticate using token based authentication;
  - Ensure you are applying this configuration to a Heatmiser NeoHub 2 or later. The Version 1 Hub does not support this
    authentication mechanism.
  - Ensure that your token is correct, this can be checked in the Heatmiser mobile app under _SETTINGS_ -> _API_ ->
    _API TOKENS_
  - Use postman to troubleshoot.

### The info command times out

- Have you tried to ping the neohub? `ping IP_ADDRESSS_HERE` if this fails the Neohub is likely unreachable for some
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
  `rm -rf /config/custom_components/heatmiserneo` restart Home Assistant and install from fresh.

## Bug Reporting and asking for help:

- Please ensure that if you wish to report a bug that is not fixed in the [Dev Branch](https://github.com/MindrustUK/Heatmiser-for-home-assistant/tree/dev) before submitting your bug.
- Include diagnostics output, logs, versions, any troubleshooting attempted, outputs and expected vs observed behaviour.
- Please note "It doesn't work" and other vague "It's broken" messages will only prompt a lot of questions to understand
  why things are broken, the more information upfront will help expedite any advice and resolution.

## Diagnostics

- You can download diagnostics from any of the device information pages
  ![Diagnostics](/images/faq_1.png)
