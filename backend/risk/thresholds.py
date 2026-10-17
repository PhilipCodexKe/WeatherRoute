"""
Weather risk level enumeration and threshold mapping.

Threshold Specifications:
- Wind (mph):
    Low:       < 25 mph
    Moderate:  25 <= speed < 35 mph
    High:      35 <= speed < 45 mph
    Severe:    45 <= speed < 55 mph
    No Travel: >= 55 mph

- Rain (in/hr):
    Low:       < 0.10 in/hr
    Moderate:  0.10 <= rain < 0.25 in/hr
    High:      0.25 <= rain < 0.50 in/hr
    Severe:    0.50 <= rain < 1.00 in/hr
    No Travel: >= 1.00 in/hr

- Snow (in/hr):
    Low:       < 0.50 in/hr
    Moderate:  0.50 <= snow < 1.00 in/hr
    High:      1.00 <= snow < 2.00 in/hr
    Severe:    2.00 <= snow < 3.00 in/hr
    No Travel: >= 3.00 in/hr
"""

from enum import IntEnum
from typing import NamedTuple


class RiskLevel(IntEnum):
    LOW = 1
    MODERATE = 2
    HIGH = 3
    SEVERE = 4
    NO_TRAVEL = 5

    @property
    def label(self) -> str:
        names = {
            RiskLevel.LOW: "Low",
            RiskLevel.MODERATE: "Moderate",
            RiskLevel.HIGH: "High",
            RiskLevel.SEVERE: "Severe",
            RiskLevel.NO_TRAVEL: "No Travel",
        }
        return names[self]


def classify_wind(wind_mph: float) -> RiskLevel:
    """Classify sustained wind speed in mph."""
    if wind_mph >= 55.0:
        return RiskLevel.NO_TRAVEL
    if wind_mph >= 45.0:
        return RiskLevel.SEVERE
    if wind_mph >= 35.0:
        return RiskLevel.HIGH
    if wind_mph >= 25.0:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def classify_rain(rain_in_per_hr: float) -> RiskLevel:
    """Classify precipitation (rain) intensity in inches/hour."""
    if rain_in_per_hr >= 1.00:
        return RiskLevel.NO_TRAVEL
    if rain_in_per_hr >= 0.50:
        return RiskLevel.SEVERE
    if rain_in_per_hr >= 0.25:
        return RiskLevel.HIGH
    if rain_in_per_hr >= 0.10:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def classify_snow(snow_in_per_hr: float) -> RiskLevel:
    """Classify snowfall intensity in inches/hour."""
    if snow_in_per_hr >= 3.00:
        return RiskLevel.NO_TRAVEL
    if snow_in_per_hr >= 2.00:
        return RiskLevel.SEVERE
    if snow_in_per_hr >= 1.00:
        return RiskLevel.HIGH
    if snow_in_per_hr >= 0.50:
        return RiskLevel.MODERATE
    return RiskLevel.LOW
