"""
REST Framework Serializers for Trip Analysis and Geocoding.
"""

from rest_framework import serializers


class GeocodeRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=256, required=True)


class AnalyzeTripRequestSerializer(serializers.Serializer):
    origin = serializers.ListField(
        child=serializers.FloatField(),
        min_length=2,
        max_length=2,
        required=True,
        help_text="[latitude, longitude] of origin",
    )
    destination = serializers.ListField(
        child=serializers.FloatField(),
        min_length=2,
        max_length=2,
        required=True,
        help_text="[latitude, longitude] of destination",
    )
    departure_time = serializers.DateTimeField(
        required=False,
        help_text="ISO 8601 departure timestamp (defaults to current time)",
    )
    load_weight_lbs = serializers.FloatField(
        required=False,
        default=35000.0,
        min_value=0.0,
        max_value=120000.0,
        help_text="Total truck load weight in lbs (affects wind threshold safety rules)",
    )
    sampling_interval_miles = serializers.IntegerField(
        default=25,
        required=False,
        min_value=1,
        help_text="Distance between sampled weather checkpoints (10, 25, or 50 miles)",
    )

    def validate_sampling_interval_miles(self, value):
        if value not in (10, 25, 50):
            raise serializers.ValidationError(
                "sampling_interval_miles must be 10, 25, or 50."
            )
        return value

    def validate_origin(self, value):
        lat, lon = value[0], value[1]
        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            raise serializers.ValidationError("Origin coordinates out of geographic bounds.")
        return value

    def validate_destination(self, value):
        lat, lon = value[0], value[1]
        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            raise serializers.ValidationError("Destination coordinates out of geographic bounds.")
        return value
