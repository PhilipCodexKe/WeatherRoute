"""
Unit tests for geo math and checkpoint sampling.
"""

from datetime import datetime, timezone
import pytest

from routing.services.checkpoint_sampler import sample_route_checkpoints
from routing.services.geo import haversine_distance_miles, interpolate_coordinates


def test_haversine_distance_known_points():
    # NYC (40.7128, -74.0060) to Philadelphia (39.9526, -75.1652) is ~80.5 miles
    dist = haversine_distance_miles(40.7128, -74.0060, 39.9526, -75.1652)
    assert 78.0 <= dist <= 83.0


def test_interpolate_coordinates():
    # Midpoint between (0, 0) and (10, 10)
    lat, lon = interpolate_coordinates(0.0, 0.0, 10.0, 10.0, 0.5)
    assert lat == 5.0
    assert lon == 5.0


def test_checkpoint_sampling_and_eta():
    departure = datetime(2026, 10, 17, 8, 0, 0, tzinfo=timezone.utc)
    # 100-mile straight segment approx (1 deg lat is ~69 miles)
    coords = [
        (40.0, -80.0),
        (40.724, -80.0),  # ~50 miles
        (41.449, -80.0),  # ~100 miles
    ]
    # Assume 100 miles takes 2 hours (7200 seconds)
    duration_secs = 7200.0

    # Sample every 25 miles
    checkpoints = sample_route_checkpoints(
        coordinates=coords,
        total_duration_seconds=duration_secs,
        departure_time=departure,
        step_miles=25.0,
    )

    # Should have roughly 5 checkpoints: 0 mi, ~25 mi, ~50 mi, ~75 mi, ~100 mi
    assert len(checkpoints) >= 4
    assert checkpoints[0].distance_from_origin_miles == 0.0
    assert checkpoints[0].eta == departure

    # Sum of segment miles should equal total distance
    total_seg_miles = sum(cp.segment_miles for cp in checkpoints)
    last_cp_dist = checkpoints[-1].distance_from_origin_miles
    assert pytest.approx(total_seg_miles, rel=1e-2) == last_cp_dist

    # Verify ETA progresses monotonically
    for i in range(1, len(checkpoints)):
        assert checkpoints[i].eta > checkpoints[i - 1].eta
        assert checkpoints[i].distance_from_origin_miles > checkpoints[i - 1].distance_from_origin_miles
