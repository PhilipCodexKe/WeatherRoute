"""
Unit tests for Routing Providers (Mapbox and Mock).
"""

import pytest
from routing.services.routing_provider import (
    BaseRoutingProvider,
    MockRoutingProvider,
    RouteOption,
)


@pytest.mark.asyncio
async def test_mock_routing_generates_exactly_3_distinct_routes():
    provider = MockRoutingProvider()
    origin = (39.7392, -104.9903)  # Denver
    destination = (41.8781, -87.6298)  # Chicago

    routes = await provider.get_3_routes(origin, destination)

    assert len(routes) == 3
    for r in routes:
        assert isinstance(r, RouteOption)
        assert r.distance_miles > 0
        assert r.duration_seconds > 0
        assert len(r.geometry) >= 20
        # Start coordinate matches origin
        assert pytest.approx(r.geometry[0][0], abs=0.01) == origin[0]
        assert pytest.approx(r.geometry[0][1], abs=0.01) == origin[1]
        # End coordinate matches destination
        assert pytest.approx(r.geometry[-1][0], abs=0.01) == destination[0]
        assert pytest.approx(r.geometry[-1][1], abs=0.01) == destination[1]

    # Verify geometries are distinct (curvatures differ)
    r1_mid = routes[0].geometry[len(routes[0].geometry) // 2]
    r2_mid = routes[1].geometry[len(routes[1].geometry) // 2]
    r3_mid = routes[2].geometry[len(routes[2].geometry) // 2]
    assert r1_mid != r2_mid
    assert r2_mid != r3_mid
