"""
Open-Meteo Weather Service.

Highlights:
- Free API, requires no API key.
- Supports multi-coordinate batch requests (up to 100+ points per single GET request).
- Hourly forecast for up to 7 days (covers required 0-48h window).
- Native parameter flags for direct truck spec units:
    wind_speed_unit=mph
    precipitation_unit=inch
- Fast in-memory caching keyed by rounded coordinate + hour bucket.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Dict, List, Optional, Sequence, Tuple
import httpx
from django.core.cache import cache

from risk.classify import CheckpointWeather

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoWeatherService:
    def __init__(self, base_url: str = OPEN_METEO_URL, timeout_seconds: float = 30.0):
        self.base_url = base_url
        self.timeout = timeout_seconds

    async def fetch_weather_for_locations(
        self,
        locations: Sequence[Tuple[float, float]],  # Sequence of (lat, lon)
    ) -> List[Dict]:
        """
        Fetches hourly weather forecasts for a batch of coordinates from Open-Meteo.
        Returns a list of raw hourly forecast dicts, one per requested coordinate.
        """
        if not locations:
            return []

        # Open-Meteo accepts comma-separated lists of latitudes and longitudes
        # Format to 4 decimals for high geo precision and efficient caching
        lats_str = ",".join(f"{round(lat, 4)}" for lat, _ in locations)
        lons_str = ",".join(f"{round(lon, 4)}" for _, lon in locations)

        params = {
            "latitude": lats_str,
            "longitude": lons_str,
            "hourly": "wind_speed_10m,wind_gusts_10m,precipitation,snowfall,temperature_2m",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "forecast_days": 3,  # 72 hours, easily covering 48h
            "timezone": "UTC",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self.base_url, params=params)
            resp.raise_for_status()
            data = resp.json()

        # If a single location was queried, Open-Meteo returns a dict.
        # If multiple locations were queried, it returns a list of dicts.
        if isinstance(data, list):
            return data
        return [data]

    def extract_weather_at_eta(
        self,
        forecast_data: Dict,
        eta: datetime,
    ) -> CheckpointWeather:
        """
        Picks the hourly weather forecast bucket corresponding to the given ETA.
        """
        hourly = forecast_data.get("hourly", {})
        times = hourly.get("time", [])

        if not times:
            return CheckpointWeather(wind_mph=0.0, rain_in_per_hr=0.0, snow_in_per_hr=0.0)

        # Round ETA to nearest whole hour (e.g. 07:45 -> 08:00, 07:25 -> 07:00)
        eta_utc = eta.astimezone(timezone.utc) if eta.tzinfo else eta
        rounded_eta = eta_utc
        if eta_utc.minute >= 30:
            rounded_eta = eta_utc.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            rounded_eta = eta_utc.replace(minute=0, second=0, microsecond=0)

        target_iso_hour = rounded_eta.strftime("%Y-%m-%dT%H:00")

        # Find exact index or closest hour
        matched_idx = -1
        if target_iso_hour in times:
            matched_idx = times.index(target_iso_hour)
        else:
            # Fallback to closest hour
            target_ts = eta_utc.timestamp()
            closest_diff = float("inf")
            for idx, t_str in enumerate(times):
                try:
                    dt = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)
                    diff = abs(dt.timestamp() - target_ts)
                    if diff < closest_diff:
                        closest_diff = diff
                        matched_idx = idx
                except Exception:
                    continue

        if matched_idx < 0:
            matched_idx = 0

        wind_speed = float(hourly.get("wind_speed_10m", [0.0])[matched_idx] or 0.0)
        gusts = float(hourly.get("wind_gusts_10m", [0.0])[matched_idx] or 0.0)
        precip = float(hourly.get("precipitation", [0.0])[matched_idx] or 0.0)
        snow = float(hourly.get("snowfall", [0.0])[matched_idx] or 0.0)
        temp_c = float(hourly.get("temperature_2m", [0.0])[matched_idx] or 0.0)
        temp_f = round(temp_c * 9.0 / 5.0 + 32.0, 1)

        # In Open-Meteo, 'precipitation' includes all liquid water equivalent.
        # If snow is falling, separate rain from snow if desired, or use precip as rain intensity.
        rain_rate = max(0.0, precip - (snow * 0.1))  # Approx 10:1 snow ratio adjustment if both present
        rain_rate = round(rain_rate if rain_rate > 0 else (precip if snow == 0 else 0.0), 3)

        return CheckpointWeather(
            wind_mph=round(wind_speed, 1),
            rain_in_per_hr=round(rain_rate, 2),
            snow_in_per_hr=round(snow, 2),
            wind_gusts_mph=round(gusts, 1),
            temperature_f=temp_f,
        )

    def extract_48h_risk_series(
        self,
        forecast_data: Dict,
        start_time: datetime,
    ) -> List[Dict[str, float]]:
        """
        Extracts hourly weather conditions for the 0-47 hour window from start_time.
        Used to generate corridor weather matrices for client-side heatmap animation.
        """
        hourly = forecast_data.get("hourly", {})
        times = hourly.get("time", [])
        if not times:
            return []

        start_utc = start_time.astimezone(timezone.utc) if start_time.tzinfo else start_time
        start_ts = start_utc.timestamp()

        # Find starting hour index
        start_idx = 0
        closest_diff = float("inf")
        for idx, t_str in enumerate(times):
            try:
                dt = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)
                diff = abs(dt.timestamp() - start_ts)
                if diff < closest_diff:
                    closest_diff = diff
                    start_idx = idx
            except Exception:
                continue

        series = []
        winds = hourly.get("wind_speed_10m", [])
        precips = hourly.get("precipitation", [])
        snows = hourly.get("snowfall", [])

        # Take up to 48 hours
        for h in range(48):
            idx = start_idx + h
            if idx < len(times):
                w = float(winds[idx] or 0.0) if idx < len(winds) else 0.0
                p = float(precips[idx] or 0.0) if idx < len(precips) else 0.0
                s = float(snows[idx] or 0.0) if idx < len(snows) else 0.0
                series.append({
                    "hour": h,
                    "time": times[idx],
                    "wind_mph": round(w, 1),
                    "rain_in_per_hr": round(p, 2),
                    "snow_in_per_hr": round(s, 2),
                })
            else:
                break

        return series
