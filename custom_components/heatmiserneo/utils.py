# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
"""Common utility functions used by multiple Heatmiser Neo modules."""

from datetime import timedelta
from enum import Enum

import voluptuous as vol

from homeassistant.helpers import config_validation as cv


def _time_period_minutes(value: float | str) -> timedelta:
    """Validate and transform minutes to a time offset."""
    try:
        return timedelta(minutes=float(value))
    except (ValueError, TypeError) as err:
        raise vol.Invalid(f"Expected minutes, got {value}") from err


hold_duration_validation = vol.All(
    vol.Any(cv.time_period_str, _time_period_minutes, timedelta, cv.time_period_dict),
    cv.positive_timedelta,
)


def unique_id_is_mac(unique_id: str | None) -> bool:
    "Check if a unique id is a mac address."
    if not unique_id:
        return False
    return unique_id.count(":") == 5 and len(unique_id) == 17


def to_dict(item):
    """Convert an arbitrary object to a dict."""
    match item:
        case dict():
            return {key: to_dict(value) for key, value in item.items()}
        case list() | tuple():
            return [to_dict(x) for x in item]
        case Enum():
            return item.name
        case timedelta():
            return {
                "days": item.days,
                "seconds": item.seconds,
                "microseconds": item.microseconds,
            }
        case object(__dict__=_):
            return {key: to_dict(value) for key, value in vars(item).items()}
        case _:
            return item
