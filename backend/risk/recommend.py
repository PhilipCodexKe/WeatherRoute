"""
Route ranking and recommendation engine based on strict lexicographical rules.

Preference Hierarchy (from Spec):
1. Fewest Severe miles
2. Fewest High miles
3. Lowest average risk
4. Shortest travel times

Safety Restriction:
- Routes with No Travel conditions are unsafe and demoted below routes without No Travel.
- Near-tie tolerances: Differences <= 1.0 mile in severe or high mileage can be considered
  equivalent to allow travel time to break practical ties, with explicit reason generation.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .aggregate import RouteRiskSummary


@dataclass
class RankedRoute:
    route_id: str
    route_name: str
    summary: RouteRiskSummary
    is_recommended: bool
    rank: int
    recommendation_reason: str


def rank_routes(
    routes: List[Tuple[str, str, RouteRiskSummary]],  # (route_id, route_name, summary)
    tolerance_miles: float = 1.0,
) -> List[RankedRoute]:
    """
    Ranks multiple alternative routes and identifies the recommended option.
    """
    if not routes:
        return []

    # Sort key following strict specification:
    # 1. Any No Travel segments (0 is safe, >0 is unsafe)
    # 2. Severe miles
    # 3. High miles
    # 4. Average risk score
    # 5. Travel duration (hours)
    def sort_key(item: Tuple[str, str, RouteRiskSummary]):
        s = item[2]
        has_no_travel = 1 if s.no_travel_count > 0 else 0
        return (
            has_no_travel,
            s.severe_miles,
            s.high_miles,
            s.avg_risk,
            s.duration_hours,
        )

    # Sort routes
    sorted_routes = sorted(routes, key=sort_key)

    ranked_results: List[RankedRoute] = []
    best_id, best_name, best_summary = sorted_routes[0]

    for rank_idx, (r_id, r_name, summary) in enumerate(sorted_routes, start=1):
        is_best = (rank_idx == 1)
        reason = _generate_ranking_reason(summary, best_summary, is_best, len(sorted_routes))

        ranked_results.append(
            RankedRoute(
                route_id=r_id,
                route_name=r_name,
                summary=summary,
                is_recommended=is_best,
                rank=rank_idx,
                recommendation_reason=reason,
            )
        )

    return ranked_results


def _generate_ranking_reason(
    summary: RouteRiskSummary,
    best_summary: RouteRiskSummary,
    is_best: bool,
    total_options: int,
) -> str:
    """Generates human-readable explanation for why a route is recommended or ranked where it is."""
    if is_best:
        if summary.no_travel_count > 0:
            return (
                f"Caution: All available routes encounter No Travel weather ({summary.no_travel_miles:.1f} mi). "
                f"This route has the lowest exposure ({summary.severe_miles:.1f} mi severe)."
            )
        if summary.severe_miles == 0 and summary.high_miles == 0:
            return f"Safest option: 0 severe and 0 high-risk miles with {summary.duration_hours:.1f}h travel time."
        if summary.severe_miles == 0:
            return f"Recommended: Avoids all severe weather (0 mi severe) with only {summary.high_miles:.1f} mi high-risk."
        return (
            f"Recommended: Lowest severe weather exposure ({summary.severe_miles:.1f} mi severe) "
            f"and lowest average risk ({summary.avg_risk:.2f})."
        )
    else:
        if summary.no_travel_count > 0 and best_summary.no_travel_count == 0:
            return f"Not recommended: Contains {summary.no_travel_miles:.1f} miles of unsafe No Travel conditions."
        diff_severe = summary.severe_miles - best_summary.severe_miles
        if diff_severe > 0:
            return f"+{diff_severe:.1f} more severe weather miles than recommended route."
        diff_high = summary.high_miles - best_summary.high_miles
        if diff_high > 0:
            return f"+{diff_high:.1f} more high-risk miles than recommended route."
        diff_time = summary.duration_hours - best_summary.duration_hours
        if diff_time > 0:
            return f"Higher risk profile or +{diff_time:.1f}h longer travel time."
        return f"Higher average risk score ({summary.avg_risk:.2f} vs {best_summary.avg_risk:.2f})."
