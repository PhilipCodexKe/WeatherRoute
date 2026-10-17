"""
URL configuration for routing app.
"""

from django.urls import path
from .views import analyze_trip, geocode_location
from rest_framework.response import Response
from rest_framework.decorators import api_view


@api_view(['GET'])
def health_check(request):
    return Response({
        "status": "healthy",
        "service": "weather-aware-truck-routing-api",
    })


urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('geocode/', geocode_location, name='geocode_location'),
    path('analyze/', analyze_trip, name='analyze_trip'),
]
