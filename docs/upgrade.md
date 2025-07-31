---
title: Upgrade Guide
nav_order: 9
---

# Upgrade to 3.2.x

[Issue 294](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/294) was raised soon after the release of v3.2.1. There are still installations where the advice of the release on 20240928 to delete and re-configure the hub was not followed and this can cause an issue when upgrading to this version. In later releases (eg after v3.2.1), an issue is raised and a fix is offered to the user to automatically cleanup the old device entries. Users just need to accept the fix and the integration will start working again.

# Upgrade 1.6 to 3.0

This is a major upgrade with a lot of changes. The recommendation is to delete and re-add the integration config entry. This will be the cleanest solution, though you might need to clean up any existing references to old entities that have been renamed or replaced. The main climate entities (eg thermostats) should not have changed. You can choose to simply upgrade and then manually delete any entities that are not longer provided by the integration.

## Summary of breaking changes changes

- Entity naming has been cleaned up (entity ids might have changed)
- Various controls for the Hold service have been removed (most of these didn't work properly)
  - For thermostats, you can now use the Boost preset (which boosts the set temperature by 2 degrees for 30 minutes), or you can use the `heatmiserneo.hold_on` service to set a custom duration and temperature
  - For timers, you can use the new mode selector and set to Override On or Override Off (which holds the state for 30 minutes). You can use the `heatmiserneo.timer_hold_on` to set a custom duration

## PRs included

- [PR #200](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/200)
- [PR #201](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/201)
- [PR #203](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/203)
- [PR #207](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/207)
- [PR #211](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/211)
- [PR #212](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/212)
- [PR #213](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/213)
- [PR #214](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/214)
- [PR #216](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/216)
- [PR #219](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/219)
- [PR #220](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/220)
- [PR #221](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/221)
- [PR #222](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/222)
- [PR #223](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/223)
- [PR #224](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/224)
- [PR #225](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/225)
- [PR #226](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/226)
- [PR #227](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/227)
- [PR #228](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/228)
- [PR #229](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/229)
- [PR #230](https://github.com/MindrustUK/Heatmiser-for-home-assistant/pull/230)

## Issues fixed/Features added

- [Issue #27](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/27)
- [Issue #46](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/46)
- [Issue #142](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/142)
- [Issue #158](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/158)
- [Issue #165](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/165)
- [Issue #177](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/177)
- [Issue #182](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/182)
- [Issue #183](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/183)
- [Issue #189](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/189)
- [Issue #194](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/194)
- [Issue #196](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/196)
- [Issue #199](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/199)
- [Issue #202](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/202)
- [Issue #206](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/206)
- [Issue #208](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/208)
- [Issue #210](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/210)
- [Issue #215](https://github.com/MindrustUK/Heatmiser-for-home-assistant/issues/215)
