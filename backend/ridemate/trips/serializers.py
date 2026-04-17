from rest_framework import serializers

from .models import Trip, Booking


class TripSerializer(serializers.ModelSerializer):
    driver = serializers.ReadOnlyField(source="driver.id")

    class Meta:
        model = Trip
        fields = [
            "id",
            "source",
            "destination",
            "date",
            "time",
            "available_seats",
            "price",
            "driver",
            "is_completed",
        ]

    def validate(self, attrs):
        source = attrs.get("source")
        destination = attrs.get("destination")
        if source and destination and source.strip().lower() == destination.strip().lower():
            raise serializers.ValidationError("Source and destination cannot be the same.")
        return attrs

    def validate_available_seats(self, value):
        if value <= 0:
            raise serializers.ValidationError("Available seats must be at least 1.")
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price must be 0 or more.")
        return value


class BookingSerializer(serializers.ModelSerializer):
    rider = serializers.ReadOnlyField(source="rider.id")
    trip = serializers.ReadOnlyField(source="trip.id")
    trip_details = TripSerializer(source="trip", read_only=True)
    driver_name = serializers.ReadOnlyField(source="trip.driver.username")

    class Meta:
        model = Booking
        fields = [
            "id",
            "trip",
            "trip_details",
            "driver_name",
            "rider",
            "seats",
            "created_at",
        ]

    def validate_seats(self, value):
        if value <= 0:
            raise serializers.ValidationError("Seats must be at least 1.")
        return value
