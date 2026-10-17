"""
Aggregation of route segment miles by risk level and calculation of route metrics.
"""

from dataclasses import dataclass
from typing import List, Sequence

from .classify import EvaluatedRisk
from .thresholds import RiskLevel


@dataclass(frozen=True)
class CheckpointResult:
    index: int
    lat: float
    lon: float
    distance_miles: float      # Cumulative distance from the origination
    eta_iso: str               # ISO timestamp for the checkpoint ETA
    segment_miles: float       # Miles represented by this checkpoint
    weather: dict              # Raw weather params
    risk: EvaluatedRisk        # Evaluated risk object


@dataclass(frozen=True)
class RouteRiskSummary:
    total_miles: float
    duration_hours: float
    severe_miles: float
    high_miles: float
    moderate_miles: float
    low_miles: float
    no_travel_miles: float
    no_travel_count: int
    avg_risk: float            # average risk score (1.0 to 5.0)


def aggregate_route_risk(
    checkpoints: Sequence[CheckpointResult],
    total_duration_hours: float,
) -> RouteRiskSummary:
    """
    Computes distance-weighted mileage for each risk category along a route.
    """
    severe_mi = 0.0
    high_mi = 0.0
    mod_mi = 0.0
    low_mi = 0.0
    no_travel_mi = 0.0
    no_travel_cnt = 0
    total_weighted_risk = 0.0
    total_miles = 0.0

    for cp in checkpoints:
        miles = cp.segment_miles
        total_miles += miles
        level = cp.risk.final_risk
        total_weighted_risk += miles * float(level.value)

        if level == RiskLevel.NO_TRAVEL:
            no_travel_mi += miles
            no_travel_cnt += 1
        elif level == RiskLevel.SEVERE:
            severe_mi += miles
        elif level == RiskLevel.HIGH:
            high_mi += miles
        elif level == RiskLevel.MODERATE:
            mod_mi += miles
        else:
            low_mi += miles

    avg_risk = (total_weighted_risk / total_miles) if total_miles > 0 else 1.0

    return RouteRiskSummary(
        total_miles=round(total_miles, 2),
        duration_hours=round(total_duration_hours, 2),
        severe_miles=round(severe_mi, 2),
        high_miles=round(high_mi, 2),
        moderate_miles=round(mod_mi, 2),
        low_miles=round(low_mi, 2),
        no_travel_miles=round(no_travel_mi, 2),
        no_travel_count=no_travel_cnt,
        avg_risk=round(avg_risk, 2),
    )
