"""
Unit tests for Open-Meteo weather provider data extraction and batch parsing.
"""

from datetime import datetime, timezone
import pytest

from risk.classify import CheckpointWeather
from routing.services.weather_provider import OpenMeteoWeatherService


@pytest.fixture
def mock_open_meteo_payload():
    return {
        "latitude": 40.0,
        "longitude": -80.0,
        "hourly": {
            "time": [
                "2026-10-17T06:00",
                "2026-10-17T07:00",
                "2026-10-17T08:00",
                "2026-10-17T09:00",
            ],
            "wind_speed_10m": [15.2, 38.5, 52.0, 58.1],
            "wind_gusts_10m": [22.0, 48.0, 65.0, 72.0],
            "precipitation": [0.05, 0.35, 1.20, 0.0],
            "snowfall": [0.0, 0.0, 0.5, 3.5],
            "temperature_2m": [10.0, 8.0, 0.0, -2.0],
        }
    }


def test_extract_weather_at_exact_eta(mock_open_meteo_payload):
    service = OpenMeteoWeatherService()
    eta = datetime(2026, 10, 17, 7, 0, 0, tzinfo=timezone.utc)
    weather = service.extract_weather_at_eta(mock_open_meteo_payload, eta)

    assert weather.wind_mph == 38.5
    assert weather.wind_gusts_mph == 48.0
    assert weather.rain_in_per_hr == 0.35
    assert weather.snow_in_per_hr == 0.0


def test_extract_weather_at_intermediate_eta(mock_open_meteo_payload):
    service = OpenMeteoWeatherService()
    # 7:25 -> Closest hour is 7:00
    eta = datetime(2026, 10, 17, 7, 25, 0, tzinfo=timezone.utc)
    weather = service.extract_weather_at_eta(mock_open_meteo_payload, eta)
    assert weather.wind_mph == 38.5

    # 7:45 -> Closest hour is 8:00
    eta2 = datetime(2026, 10, 17, 7, 45, 0, tzinfo=timezone.utc)
    weather2 = service.extract_weather_at_eta(mock_open_meteo_payload, eta2)
    assert weather2.wind_mph == 52.0


def test_extract_48h_risk_series(mock_open_meteo_payload):
    service = OpenMeteoWeatherService()
    start = datetime(2026, 10, 17, 6, 0, 0, tzinfo=timezone.utc)
    series = service.extract_48h_risk_series(mock_open_meteo_payload, start)

    assert len(series) == 4
    assert series[0]["hour"] == 0
    assert series[0]["wind_mph"] == 15.2
    assert series[3]["hour"] == 3
    assert series[3]["wind_mph"] == 58.1
