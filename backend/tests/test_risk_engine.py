"""
Comprehensive unit tests for the Risk Engine:
1. Wind, Rain, and Snow boundary threshold classifications
2. Load weight adjustments (30k, 40k, 55+ mph)
3. Multi-hazard max severity logic
4. Mile-weighted risk aggregation
5. Lexicographical route recommendation priority & tie-breaking
"""

import pytest

from risk.aggregate import CheckpointResult, aggregate_route_risk
from risk.classify import CheckpointWeather, evaluate_checkpoint_risk
from risk.recommend import rank_routes
from risk.thresholds import RiskLevel, classify_rain, classify_snow, classify_wind


# ==========================================
# 1. Weather Thresholds Boundary Tests
# ==========================================

@pytest.mark.parametrize(
    "wind_mph, expected",
    [
        (0.0, RiskLevel.LOW),
        (24.9, RiskLevel.LOW),
        (25.0, RiskLevel.MODERATE),
        (34.9, RiskLevel.MODERATE),
        (35.0, RiskLevel.HIGH),
        (44.9, RiskLevel.HIGH),
        (45.0, RiskLevel.SEVERE),
        (54.9, RiskLevel.SEVERE),
        (55.0, RiskLevel.NO_TRAVEL),
        (75.0, RiskLevel.NO_TRAVEL),
    ],
)
def test_wind_thresholds(wind_mph, expected):
    assert classify_wind(wind_mph) == expected


@pytest.mark.parametrize(
    "rain_in, expected",
    [
        (0.0, RiskLevel.LOW),
        (0.09, RiskLevel.LOW),
        (0.10, RiskLevel.MODERATE),
        (0.24, RiskLevel.MODERATE),
        (0.25, RiskLevel.HIGH),
        (0.49, RiskLevel.HIGH),
        (0.50, RiskLevel.SEVERE),
        (0.99, RiskLevel.SEVERE),
        (1.00, RiskLevel.NO_TRAVEL),
        (2.50, RiskLevel.NO_TRAVEL),
    ],
)
def test_rain_thresholds(rain_in, expected):
    assert classify_rain(rain_in) == expected


@pytest.mark.parametrize(
    "snow_in, expected",
    [
        (0.0, RiskLevel.LOW),
        (0.49, RiskLevel.LOW),
        (0.50, RiskLevel.MODERATE),
        (0.99, RiskLevel.MODERATE),
        (1.00, RiskLevel.HIGH),
        (1.99, RiskLevel.HIGH),
        (2.00, RiskLevel.SEVERE),
        (2.99, RiskLevel.SEVERE),
        (3.00, RiskLevel.NO_TRAVEL),
        (5.00, RiskLevel.NO_TRAVEL),
    ],
)
def test_snow_thresholds(snow_in, expected):
    assert classify_snow(snow_in) == expected


# ==========================================
# 2. Load-Specific Wind Escalation Tests
# ==========================================

def test_wind_55_plus_no_travel_for_any_load():
    # Light load (10,000 lbs) with 55 mph wind -> NO_TRAVEL
    w = CheckpointWeather(wind_mph=56.0, rain_in_per_hr=0.0, snow_in_per_hr=0.0)
    res = evaluate_checkpoint_risk(w, load_weight_lbs=10000)
    assert res.final_risk == RiskLevel.NO_TRAVEL

    # Heavy load (60,000 lbs) with 55 mph wind -> NO_TRAVEL
    res2 = evaluate_checkpoint_risk(w, load_weight_lbs=60000)
    assert res2.final_risk == RiskLevel.NO_TRAVEL


def test_wind_45_to_54_with_heavy_load_rule():
    w = CheckpointWeather(wind_mph=48.0, rain_in_per_hr=0.0, snow_in_per_hr=0.0)

    # <= 30,000 lbs: Remains SEVERE (wind is 48 mph)
    res_light = evaluate_checkpoint_risk(w, load_weight_lbs=30000)
    assert res_light.final_risk == RiskLevel.SEVERE
    assert res_light.load_adjustment_applied is None

    # > 30,000 lbs: Escalated to NO_TRAVEL
    res_heavy = evaluate_checkpoint_risk(w, load_weight_lbs=30001)
    assert res_heavy.final_risk == RiskLevel.NO_TRAVEL
    assert "No Travel" in res_heavy.load_adjustment_applied


def test_wind_35_to_44_with_heavy_load_rule():
    w = CheckpointWeather(wind_mph=38.0, rain_in_per_hr=0.0, snow_in_per_hr=0.0)

    # <= 40,000 lbs: Remains HIGH
    res_light = evaluate_checkpoint_risk(w, load_weight_lbs=40000)
    assert res_light.final_risk == RiskLevel.HIGH
    assert res_light.load_adjustment_applied is None

    # > 40,000 lbs: Escalated to SEVERE
    res_heavy = evaluate_checkpoint_risk(w, load_weight_lbs=40001)
    assert res_heavy.final_risk == RiskLevel.SEVERE
    assert "Severe" in res_heavy.load_adjustment_applied


def test_max_hazard_combination():
    # Rain is Moderate, Wind is High, Snow is Severe -> Base & Final must be Severe
    w = CheckpointWeather(wind_mph=36.0, rain_in_per_hr=0.15, snow_in_per_hr=2.2)
    res = evaluate_checkpoint_risk(w, load_weight_lbs=20000)
    assert res.base_risk == RiskLevel.SEVERE
    assert res.final_risk == RiskLevel.SEVERE


# ==========================================
# 3. Route Aggregation & Recommendation Tests
# ==========================================

def test_mile_weighted_aggregation():
    # Checkpoint 1: 50 miles of Low (score 1)
    # Checkpoint 2: 50 miles of Severe (score 4)
    r_low = evaluate_checkpoint_risk(CheckpointWeather(10, 0, 0), 20000)
    r_sev = evaluate_checkpoint_risk(CheckpointWeather(48, 0, 0), 20000)

    cp1 = CheckpointResult(
        index=0, lat=40.0, lon=-80.0, distance_miles=0.0, eta_iso="2026-10-17T06:00:00Z",
        segment_miles=50.0, weather={}, risk=r_low
    )
    cp2 = CheckpointResult(
        index=1, lat=40.5, lon=-80.5, distance_miles=50.0, eta_iso="2026-10-17T07:00:00Z",
        segment_miles=50.0, weather={}, risk=r_sev
    )

    summary = aggregate_route_risk([cp1, cp2], total_duration_hours=2.0)
    assert summary.total_miles == 100.0
    assert summary.low_miles == 50.0
    assert summary.severe_miles == 50.0
    assert summary.avg_risk == 2.5  # (50*1 + 50*4)/100 = 2.50


def test_lexicographical_ranking_hierarchy():
    # Route A: 0 Severe, 20 High, 6.0 hours
    # Route B: 10 Severe, 0 High, 5.0 hours (Faster, but has severe miles)
    # Route C: Contains No Travel (disqualified/ranked lowest)
    from risk.aggregate import RouteRiskSummary

    summary_a = RouteRiskSummary(
        total_miles=300, duration_hours=6.0, severe_miles=0.0, high_miles=20.0,
        moderate_miles=80.0, low_miles=200.0, no_travel_miles=0.0, no_travel_count=0, avg_risk=1.8
    )
    summary_b = RouteRiskSummary(
        total_miles=280, duration_hours=5.0, severe_miles=10.0, high_miles=0.0,
        moderate_miles=70.0, low_miles=200.0, no_travel_miles=0.0, no_travel_count=0, avg_risk=1.9
    )
    summary_c = RouteRiskSummary(
        total_miles=270, duration_hours=4.5, severe_miles=0.0, high_miles=0.0,
        moderate_miles=50.0, low_miles=200.0, no_travel_miles=20.0, no_travel_count=1, avg_risk=2.2
    )

    ranked = rank_routes([
        ("route_b", "Route 2 (Shortest)", summary_b),
        ("route_a", "Route 1 (Safest)", summary_a),
        ("route_c", "Route 3 (Unsafe)", summary_c),
    ])

    # Rule 1: Fewest Severe miles -> Route A (0 severe) beats Route B (10 severe) despite Route B being faster!
    # Rule Safety: Route C has No Travel, so it ranks 3rd
    assert ranked[0].route_id == "route_a"
    assert ranked[0].is_recommended is True
    assert ranked[1].route_id == "route_b"
    assert ranked[2].route_id == "route_c"
