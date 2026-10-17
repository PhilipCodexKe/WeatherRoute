"""
Checkpoint sampling service along route polylines.

Features:
- Samples points along the true geometry every N miles (e.g. 10, 25, 50 mi).
- Interpolates the truck's arrival time (ETA) based on cumulative route duration.
- Attributes miles to each checkpoint using midpoint intervals for fair risk weighting.
- Always ensures Origin (start) and Destination (end) are captured.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Sequence, Tuple

from .geo import haversine_distance_miles, interpolate_coordinates


@dataclass(frozen=True)
class SampledCheckpoint:
    index: int
    lat: float
    lon: float
    distance_from_origin_miles: float
    eta: datetime
    segment_miles: float  # Miles of the route represented by this checkpoint


def sample_route_checkpoints(
    coordinates: Sequence[Tuple[float, float]],  # List of (lat, lon)
    total_duration_seconds: float,
    departure_time: datetime,
    step_miles: float = 25.0,
) -> List[SampledCheckpoint]:
    """
    Samples checkpoints along a polyline at regular mile intervals.
    """
    if not coordinates:
        return []

    if len(coordinates) == 1:
        return [
            SampledCheckpoint(
                index=0,
                lat=coordinates[0][0],
                lon=coordinates[0][1],
                distance_from_origin_miles=0.0,
                eta=departure_time,
                segment_miles=0.0,
            )
        ]

    # 1. Compute cumulative distances along the polyline vertices
    vertex_distances = [0.0]
    total_distance = 0.0

    for i in range(1, len(coordinates)):
        lat1, lon1 = coordinates[i - 1]
        lat2, lon2 = coordinates[i]
        seg_dist = haversine_distance_miles(lat1, lon1, lat2, lon2)
        total_distance += seg_dist
        vertex_distances.append(total_distance)

    # If the entire route is shorter than or roughly equal to one step, return origin + destination
    if total_distance <= step_miles:
        eta_end = departure_time + timedelta(seconds=total_duration_seconds)
        half_dist = total_distance / 2.0
        return [
            SampledCheckpoint(
                index=0,
                lat=coordinates[0][0],
                lon=coordinates[0][1],
                distance_from_origin_miles=0.0,
                eta=departure_time,
                segment_miles=round(half_dist, 2),
            ),
            SampledCheckpoint(
                index=1,
                lat=coordinates[-1][0],
                lon=coordinates[-1][1],
                distance_from_origin_miles=round(total_distance, 2),
                eta=eta_end,
                segment_miles=round(half_dist, 2),
            ),
        ]

    # 2. Determine target sampling mile markers: 0.0, step, 2*step, ..., and total_distance
    target_mile_markers: List[float] = [0.0]
    curr_target = step_miles
    while curr_target < total_distance - (step_miles * 0.35):  # Avoid clustering near the very end
        target_mile_markers.append(round(curr_target, 2))
        curr_target += step_miles

    target_mile_markers.append(round(total_distance, 2))

    # 3. Interpolate (lat, lon) and compute ETA for each target marker
    sampled_points: List[SampledCheckpoint] = []
    vertex_idx = 0

    for idx, target_dist in enumerate(target_mile_markers):
        # Progress vertex_idx until vertex_distances[vertex_idx + 1] >= target_dist
        while vertex_idx < len(coordinates) - 2 and vertex_distances[vertex_idx + 1] < target_dist:
            vertex_idx += 1

        seg_start_dist = vertex_distances[vertex_idx]
        seg_end_dist = vertex_distances[vertex_idx + 1]
        seg_len = seg_end_dist - seg_start_dist

        if seg_len > 0.0001:
            frac = (target_dist - seg_start_dist) / seg_len
        else:
            frac = 0.0

        lat1, lon1 = coordinates[vertex_idx]
        lat2, lon2 = coordinates[vertex_idx + 1]
        lat, lon = interpolate_coordinates(lat1, lon1, lat2, lon2, frac)

        # ETA interpolation based on cumulative distance fraction
        time_fraction = (target_dist / total_distance) if total_distance > 0 else 0.0
        eta = departure_time + timedelta(seconds=round(total_duration_seconds * time_fraction))

        sampled_points.append(
            SampledCheckpoint(
                index=idx,
                lat=lat,
                lon=lon,
                distance_from_origin_miles=target_dist,
                eta=eta,
                segment_miles=0.0,  # Calculated in step 4 below
            )
        )

    # 4. Attribute segment miles to each checkpoint via midpoints
    attributed_checkpoints: List[SampledCheckpoint] = []
    n = len(sampled_points)

    for i in range(n):
        curr = sampled_points[i]
        if n == 1:
            seg_mi = total_distance
        elif i == 0:
            # Distance from 0 to midpoint with next checkpoint
            next_pt = sampled_points[i + 1]
            seg_mi = (next_pt.distance_from_origin_miles - curr.distance_from_origin_miles) / 2.0
        elif i == n - 1:
            # Distance from midpoint with prev checkpoint to end
            prev_pt = sampled_points[i - 1]
            seg_mi = (curr.distance_from_origin_miles - prev_pt.distance_from_origin_miles) / 2.0
        else:
            # Distance between midpoint behind and midpoint ahead
            prev_pt = sampled_points[i - 1]
            next_pt = sampled_points[i + 1]
            seg_mi = (next_pt.distance_from_origin_miles - prev_pt.distance_from_origin_miles) / 2.0

        attributed_checkpoints.append(
            SampledCheckpoint(
                index=curr.index,
                lat=curr.lat,
                lon=curr.lon,
                distance_from_origin_miles=curr.distance_from_origin_miles,
                eta=curr.eta,
                segment_miles=round(seg_mi, 2),
            )
        )

    return attributed_checkpoints
