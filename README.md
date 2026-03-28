<!-- SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
-->

![GitHub release](https://img.shields.io/github/v/release/MindrustUK/Heatmiser-for-home-assistant) ![Integration Installs](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.heatmiserneo.total) [![Downloads for latest release](https://img.shields.io/github/downloads/MindrustUK/Heatmiser-for-home-assistant/latest/total.svg)](https://github.com/MindrustUK/Heatmiser-for-home-assistant/releases/latest) [![Community Forum](https://img.shields.io/badge/community-forum-brightgreen.svg)](https://community.home-assistant.io/t/heatmiser-neo-hub-support-ugly-and-work-in-progress)

[![Validate with hassfest](https://github.com/MindrustUK/Heatmiser-for-home-assistant/actions/workflows/validate-hassfest.yaml/badge.svg)](https://github.com/MindrustUK/Heatmiser-for-home-assistant/actions/workflows/validate-hassfest.yaml) [![HACS Validate](https://github.com/MindrustUK/Heatmiser-for-home-assistant/actions/workflows/validate-hacs.yaml/badge.svg)](https://github.com/MindrustUK/Heatmiser-for-home-assistant/actions/workflows/validate-hacs.yaml) [![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://www.hacs.xyz/)

# Heatmiser-for-home-assistant

An integration for [Home Assistant](https://www.home-assistant.io/) to add support for [Heatmiser's Neo-Hub and 'Neo'](https://www.heatmiser.com/en/heatmiser-neo-overview/) range of products.

This is a work in progress for adding Heatmiser Neo-hub support to Home Assistant (https://home-assistant.io/), I maintain this as a weekend project only so don't expect fast updates but feel free to raise issues as needed.

# Documentation

Full documentation is available here - [Heatmiser for Home Assistant](https://mindrustuk.github.io/Heatmiser-for-home-assistant/)

## Change log

[Change Log](https://github.com/MindrustUK/Heatmiser-for-home-assistant/blob/dev/docs/changelog.md)

# Known issues - Read me first!

- Note specifically the NeoStat WiFi device does not have an API, and so cannot be used with this (or any) NeoHub-based integration.

# Supporting this project

As per: [https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/133](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/133) a few users found this useful and
wanted to support the project. I'm very grateful and humbled, thanks for the show of support!

This is not a completely solo project, and credit is due to anyone who contributed. Please see the GitHub commits
to support these awesome devs if there was any work that you would like to say thanks for.

I'd particularly like to call out

- ocrease: [https://github.com/ocrease](https://github.com/ocrease) for massive contributions to code clean up,
  feature enhancement and lots of bug fixes.

- Andrius Štikonas: [https://gitlab.com/neohubapi/neohubapi/](https://gitlab.com/neohubapi/neohubapi/) or [https://stikonas.eu/](https://stikonas.eu/) for migrating the
  original API calls to a Home Assistant compatible library, and maintaining its release.

Please consider supporting their efforts!

I've setup the following to accept donations to support my work;

[https://ko-fi.com/MindrustUK](https://ko-fi.com/MindrustUK)

[https://liberapay.com/MindrustUK](https://liberapay.com/MindrustUK)

If anyone from Heatmiser is reading; some more devices to build out a more complete hardware test suite to ensure
coverage would really help the project. Feel free to reach out if you want to help with this.
