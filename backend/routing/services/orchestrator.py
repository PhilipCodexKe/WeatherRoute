"""
Trip Analysis Orchestration Pipeline.

Execution Steps:
1. Fetch 3 alternative routes from RoutingProvider.
2. Sample checkpoints along each route every N miles (10, 25, 50) and compute ETA.
3. Collect all unique coordinates across routes and corridor points.
4. Batch fetch Open-Meteo forecasts — ALL chunks in parallel with asyncio.gather.
5. Evaluate weather and load-specific risk at each checkpoint.
6. Aggregate miles by risk level per route.
7. Rank routes using strict lexicographical recommendation hierarchy.
8. Build compact 48-hour corridor heatmap matrix (reuses checkpoint forecasts — zero extra API calls).
"""

import asyncio
from datetime import datetime, timezone
import logging
import math

logger = logging.getLogger(__name__)
from typing import Any, Dict, List, Optional, Set, Tuple

from risk.aggregate import CheckpointResult, RouteRiskSummary, aggregate_route_risk
from risk.classify import CheckpointWeather, evaluate_checkpoint_risk
from risk.recommend import RankedRoute, rank_routes
from .checkpoint_sampler import SampledCheckpoint, sample_route_checkpoints
from .geo import haversine_distance_miles
from .routing_provider import BaseRoutingProvider, MapboxRoutingProvider, RouteOption
from .weather_provider import OpenMeteoWeatherService

logger = logging.getLogger(__name__)


class TripAnalysisOrchestrator:
    def __init__(
        self,
        routing_provider: Optional[BaseRoutingProvider] = None,
        weather_service: Optional[OpenMeteoWeatherService] = None,
    ):
        self.routing_provider = routing_provider or MapboxRoutingProvider()
        self.weather_service = weather_service or OpenMeteoWeatherService()

    async def analyze_trip(
        self,
        origin: Tuple[float, float],           # (lat, lon)
        destination: Tuple[float, float],      # (lat, lon)
        departure_time: datetime,
        load_weight_lbs: float,
        step_miles: float = 25.0,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end trip analysis pipeline and returns unified JSON payload.
        """
        # 1. Fetch 3 routes
        routes: List[RouteOption] = await self.routing_provider.get_3_routes(origin, destination)
        if not routes:
            raise ValueError("Unable to calculate route options between the specified locations.")

        # 2. Sample checkpoints along each route
        route_checkpoints: Dict[str, List[SampledCheckpoint]] = {}
        loc_key_to_coords: Dict[str, Tuple[float, float]] = {}

        def get_loc_key(lat: float, lon: float) -> str:
            # Round to ~0.15 deg (~10 miles) — reduces unique points on long routes
            return f"{round(lat * 6.67) / 6.67:.2f},{round(lon * 6.67) / 6.67:.2f}"

        for route in routes:
            cps = sample_route_checkpoints(
                coordinates=route.geometry,
                total_duration_seconds=route.duration_seconds,
                departure_time=departure_time,
                step_miles=step_miles,
            )
            route_checkpoints[route.route_id] = cps
            for cp in cps:
                k = get_loc_key(cp.lat, cp.lon)
                if k not in loc_key_to_coords:
                    loc_key_to_coords[k] = (cp.lat, cp.lon)

        # Corridor heatmap uses the SAME checkpoint coords — no extra API calls
        corridor_sample_points = list(loc_key_to_coords.values())

        # 3. Split into chunks and fetch with bounded concurrency to avoid Open-Meteo 429s
        unique_coords_list = list(loc_key_to_coords.values())
        chunk_size = 15  # Smaller chunks = shorter URLs, less likely to hit rate limits
        chunks = [
            unique_coords_list[i: i + chunk_size]
            for i in range(0, len(unique_coords_list), chunk_size)
        ]

        # Semaphore: max 2 concurrent Open-Meteo requests (avoids 429 on long routes)
        sem = asyncio.Semaphore(2)

        async def fetch_chunk(chunk):
            async with sem:
                for attempt in range(4):
                    try:
                        return chunk, await self.weather_service.fetch_weather_for_locations(chunk)
                    except Exception as exc:
                        logger.warning("Weather fetch attempt %d failed: %s", attempt + 1, exc)
                        if attempt < 3:
                            await asyncio.sleep(0.5 * (2 ** attempt))  # 0.5s, 1s, 2s backoff
                        else:
                            logger.error("Exhausted retries for chunk: %s", exc)
                            # Return empty for this chunk rather than crashing the whole analysis
                            return chunk, [{}] * len(chunk)
                return chunk, [{}] * len(chunk)

        # Fire all chunks (bounded by semaphore)
        results = await asyncio.gather(*[fetch_chunk(c) for c in chunks])

        forecast_by_coord_key: Dict[str, Dict] = {}
        for chunk, forecasts in results:
            for coord, f_data in zip(chunk, forecasts):
                k = get_loc_key(coord[0], coord[1])
                forecast_by_coord_key[k] = f_data

        # 4. Evaluate weather risk for each checkpoint along each route
        evaluated_routes: List[Dict[str, Any]] = []
        routes_for_ranking: List[Tuple[str, str, RouteRiskSummary]] = []
        route_checkpoint_results: Dict[str, List[Dict[str, Any]]] = {}

        for route in routes:
            cps = route_checkpoints[route.route_id]
            cp_results_for_agg: List[CheckpointResult] = []
            cp_results_payload: List[Dict[str, Any]] = []

            for cp in cps:
                k = get_loc_key(cp.lat, cp.lon)
                f_data = forecast_by_coord_key.get(k, {})
                weather: CheckpointWeather = self.weather_service.extract_weather_at_eta(f_data, cp.eta)
                risk_eval = evaluate_checkpoint_risk(weather, load_weight_lbs=load_weight_lbs)

                cp_res = CheckpointResult(
                    index=cp.index,
                    lat=cp.lat,
                    lon=cp.lon,
                    distance_miles=cp.distance_from_origin_miles,
                    eta_iso=cp.eta.isoformat(),
                    segment_miles=cp.segment_miles,
                    weather={
                        "wind_mph": weather.wind_mph,
                        "wind_gusts_mph": weather.wind_gusts_mph,
                        "rain_in_per_hr": weather.rain_in_per_hr,
                        "snow_in_per_hr": weather.snow_in_per_hr,
                        "temperature_f": weather.temperature_f,
                    },
                    risk=risk_eval,
                )
                cp_results_for_agg.append(cp_res)

                cp_results_payload.append({
                    "index": cp.index,
                    "latitude": cp.lat,
                    "longitude": cp.lon,
                    "distance_miles": cp.distance_from_origin_miles,
                    "eta": cp.eta.isoformat(),
                    "segment_miles": cp.segment_miles,
                    "weather": cp_res.weather,
                    "risk": {
                        "level": risk_eval.final_risk.value,
                        "label": risk_eval.final_risk.label,
                        "base_level": risk_eval.base_risk.value,
                        "load_adjustment": risk_eval.load_adjustment_applied,
                    },
                })

            summary = aggregate_route_risk(
                checkpoints=cp_results_for_agg,
                total_duration_hours=route.duration_seconds / 3600.0,
            )
            routes_for_ranking.append((route.route_id, route.name, summary))
            route_checkpoint_results[route.route_id] = cp_results_payload

        # 5. Rank routes
        ranked_routes: List[RankedRoute] = rank_routes(routes_for_ranking)
        ranked_lookup = {r.route_id: r for r in ranked_routes}

        # Format routes for frontend
        for route in routes:
            ranking_info = ranked_lookup[route.route_id]
            evaluated_routes.append({
                "id": route.route_id,
                "name": route.name,
                "rank": ranking_info.rank,
                "is_recommended": ranking_info.is_recommended,
                "recommendation_reason": ranking_info.recommendation_reason,
                "distance_miles": route.distance_miles,
                "duration_hours": round(route.duration_seconds / 3600.0, 2),
                "summary": {
                    "total_miles": ranking_info.summary.total_miles,
                    "duration_hours": ranking_info.summary.duration_hours,
                    "severe_miles": ranking_info.summary.severe_miles,
                    "high_miles": ranking_info.summary.high_miles,
                    "moderate_miles": ranking_info.summary.moderate_miles,
                    "low_miles": ranking_info.summary.low_miles,
                    "no_travel_miles": ranking_info.summary.no_travel_miles,
                    "no_travel_count": ranking_info.summary.no_travel_count,
                    "avg_risk": ranking_info.summary.avg_risk,
                },
                "geometry": [{"latitude": lat, "longitude": lon} for lat, lon in route.geometry],
                "checkpoints": route_checkpoint_results[route.route_id],
            })

        # Sort routes so recommended route is first
        evaluated_routes.sort(key=lambda x: x["rank"])

        # 6. Build compact 48-hour corridor heatmap (reuses already-fetched forecasts)
        heatmap_corridor = self._build_corridor_heatmap_matrix(
            corridor_points=corridor_sample_points,
            forecast_lookup=forecast_by_coord_key,
            get_loc_key=get_loc_key,
            start_time=departure_time,
            load_weight_lbs=load_weight_lbs,
        )

        return {
            "origin": {"latitude": origin[0], "longitude": origin[1]},
            "destination": {"latitude": destination[0], "longitude": destination[1]},
            "departure_time": departure_time.isoformat(),
            "load_weight_lbs": load_weight_lbs,
            "sampling_interval_miles": step_miles,
            "routes": evaluated_routes,
            "corridor_heatmap": heatmap_corridor,
        }

    def _build_corridor_heatmap_matrix(
        self,
        corridor_points: List[Tuple[float, float]],
        forecast_lookup: Dict[str, Dict],
        get_loc_key: Any,
        start_time: datetime,
        load_weight_lbs: float,
    ) -> List[Dict[str, Any]]:
        """
        Builds a compact array of grid points, each with 48 integer risk levels (0-48h).
        Uses already-fetched checkpoint forecasts — zero additional API calls.
        """
        matrix: List[Dict[str, Any]] = []

        for lat, lon in corridor_points:
            k = get_loc_key(lat, lon)
            f_data = forecast_lookup.get(k, {})
            series = self.weather_service.extract_48h_risk_series(f_data, start_time)

            hourly_risks: List[int] = []
            for item in series:
                cw = CheckpointWeather(
                    wind_mph=item["wind_mph"],
                    rain_in_per_hr=item["rain_in_per_hr"],
                    snow_in_per_hr=item["snow_in_per_hr"],
                )
                evaluated = evaluate_checkpoint_risk(cw, load_weight_lbs=load_weight_lbs)
                hourly_risks.append(int(evaluated.final_risk.value))

            # Pad up to 48 if needed
            while len(hourly_risks) < 48:
                hourly_risks.append(hourly_risks[-1] if hourly_risks else 1)

            matrix.append({
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "risks": hourly_risks[:48],
            })

        return matrix
