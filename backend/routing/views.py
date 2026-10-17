"""
API Views for Geocoding and Trip Analysis.
"""

import asyncio
import sys
from datetime import datetime, timezone
import logging
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import AnalyzeTripRequestSerializer, GeocodeRequestSerializer
from .services.geocoding import GeocodingService
from .services.orchestrator import TripAnalysisOrchestrator

logger = logging.getLogger(__name__)

# On Windows, asyncio.gather requires SelectorEventLoop (not the default ProactorEventLoop)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Singletons for services
geocoding_service = GeocodingService()
orchestrator = TripAnalysisOrchestrator()


@api_view(['GET'])
def geocode_location(request):
    """
    Search for address or city coordinates.
    Query param: ?q=Denver
    """
    query = request.query_params.get('q', '').strip()
    if not query:
        return Response({"error": "Missing 'q' query parameter."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        results = asyncio.run(geocoding_service.geocode(query))
        return Response({"results": results})
    except Exception as e:
        logger.exception("Geocoding failed")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def analyze_trip(request):
    """
    Primary Trip Analysis Endpoint.
    Generates 3 route options, evaluates weather at checkpoints using arrival times,
    applies load safety rules, ranks routes, and generates a 48h corridor heatmap.
    """
    serializer = AnalyzeTripRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    origin = tuple(data['origin'])
    destination = tuple(data['destination'])
    departure_time = data.get('departure_time') or datetime.now(timezone.utc)
    load_weight_lbs = data.get('load_weight_lbs', 35000.0)
    step_miles = float(data.get('sampling_interval_miles', 25.0))

    try:
        analysis_result = asyncio.run(
            orchestrator.analyze_trip(
                origin=origin,
                destination=destination,
                departure_time=departure_time,
                load_weight_lbs=load_weight_lbs,
                step_miles=step_miles,
            )
        )
        return Response(analysis_result, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("Trip analysis failed")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
