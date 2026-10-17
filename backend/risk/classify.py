"""
Weather and load-specific risk evaluation for route checkpoints.

Load Rules (Spec):
- Wind >= 55 mph:
    -> No Travel for any load
- Wind 45-54 mph (Severe) + load > 30,000 lb:
    -> No Travel
- Wind 35-44 mph (High) + load > 40,000 lb:
    -> Severe (escalated to at least Severe)

Overall Checkpoint Classification:
- Base Risk = max(wind_risk, rain_risk, snow_risk)
- Load Adjusted Risk = escalate based on load rules
"""

from dataclasses import dataclass
from typing import Optional

from .thresholds import RiskLevel, classify_rain, classify_snow, classify_wind


@dataclass(frozen=True)
class CheckpointWeather:
    wind_mph: float
    rain_in_per_hr: float
    snow_in_per_hr: float
    wind_gusts_mph: Optional[float] = None
    temperature_f: Optional[float] = None


@dataclass(frozen=True)
class EvaluatedRisk:
    wind_risk: RiskLevel
    rain_risk: RiskLevel
    snow_risk: RiskLevel
    base_risk: RiskLevel
    final_risk: RiskLevel
    load_adjustment_applied: Optional[str] = None


def evaluate_checkpoint_risk(
    weather: CheckpointWeather,
    load_weight_lbs: float,
) -> EvaluatedRisk:
    """
    Evaluates weather risk at a single checkpoint, taking into account the truck's load weight.
    """
    w_risk = classify_wind(weather.wind_mph)
    r_risk = classify_rain(weather.rain_in_per_hr)
    s_risk = classify_snow(weather.snow_in_per_hr)

    # Base risk is the maximum severity among wind, rain, and snow
    base = max(w_risk, r_risk, s_risk)
    final = base
    adjustment = None

    # Load-specific wind escalation rules:
    # 1. Wind >= 55 mph -> No Travel for all (already caught by classify_wind, but enforced here)
    if weather.wind_mph >= 55.0:
        final = RiskLevel.NO_TRAVEL
        adjustment = "Wind >= 55 mph: No Travel for any loads"

    # 2. Wind 45-54 mph + load > 30,000 lb -> No Travel
    elif 45.0 <= weather.wind_mph < 55.0 and load_weight_lbs > 30000:
        final = RiskLevel.NO_TRAVEL
        adjustment = "Wind 45-54 mph with load > 30,000 lb: Escalated to No Travel"

    # 3. Wind 35-44 mph + load > 40,000 lb -> Severe
    elif 35.0 <= weather.wind_mph < 45.0 and load_weight_lbs > 40000:
        if final < RiskLevel.SEVERE:
            final = RiskLevel.SEVERE
            adjustment = "Wind 35-44 mph with load > 40,000 lb: Escalated to Severe"

    return EvaluatedRisk(
        wind_risk=w_risk,
        rain_risk=r_risk,
        snow_risk=s_risk,
        base_risk=base,
        final_risk=final,
        load_adjustment_applied=adjustment,
    )
