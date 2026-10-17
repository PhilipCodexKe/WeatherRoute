"""
Integration tests for the /api/analyze/ and /api/geocode/ endpoints.
"""

from datetime import datetime, timezone
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


def test_health_check_endpoint(api_client):
    response = api_client.get('/api/health/')
    assert response.status_code == 200
    assert response.data["status"] == "healthy"


def test_geocode_endpoint(api_client):
    response = api_client.get('/api/geocode/?q=Denver')
    assert response.status_code == 200
    results = response.data.get("results", [])
    assert len(results) > 0
    assert "Denver" in results[0]["place_name"]


def test_analyze_trip_endpoint_validation_error(api_client):
    # Missing required coordinates
    response = api_client.post('/api/analyze/', {}, format='json')
    assert response.status_code == 400
    assert "origin" in response.data
    assert "destination" in response.data


def test_analyze_trip_endpoint_end_to_end(api_client):
    # NYC to Philadelphia trip
    payload = {
        "origin": [40.7128, -74.0060],
        "destination": [39.9526, -75.1652],
        "departure_time": datetime.now(timezone.utc).isoformat(),
        "load_weight_lbs": 42000,
        "sampling_interval_miles": 25.0,
    }
    response = api_client.post('/api/analyze/', payload, format='json')
    assert response.status_code == 200
    data = response.data

    # Check top-level payload structure
    assert "routes" in data
    assert len(data["routes"]) == 3
    assert "corridor_heatmap" in data
    assert len(data["corridor_heatmap"]) > 0

    # Recommended route must be marked
    routes = data["routes"]
    recommended = [r for r in routes if r["is_recommended"]]
    assert len(recommended) == 1
    assert recommended[0]["rank"] == 1
    assert "recommendation_reason" in recommended[0]
    assert len(recommended[0]["checkpoints"]) > 0

    # Verify corridor heatmap has 48 values per point
    first_heatmap_pt = data["corridor_heatmap"][0]
    assert len(first_heatmap_pt["risks"]) == 48
