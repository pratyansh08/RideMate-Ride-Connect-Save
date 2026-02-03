from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Booking, Trip
from .serializers import BookingSerializer, TripSerializer


class CreateTripView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TripSerializer(data=request.data)
        if serializer.is_valid():
            trip = serializer.save(driver=request.user)
            return Response(
                TripSerializer(trip).data,
                status=status.HTTP_201_CREATED,
            )
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class TripListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        trips = Trip.objects.all().order_by("date", "time")
        serializer = TripSerializer(trips, many=True)
        return Response(serializer.data)


class TripSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        source = request.query_params.get("from")
        destination = request.query_params.get("to")
        date = request.query_params.get("date")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")
        seats = request.query_params.get("seats")

        trips = Trip.objects.all()
        if source:
            trips = trips.filter(source__icontains=source)
        if destination:
            trips = trips.filter(destination__icontains=destination)
        if date:
            trips = trips.filter(date=date)
        if date_from:
            trips = trips.filter(date__gte=date_from)
        if date_to:
            trips = trips.filter(date__lte=date_to)
        if min_price:
            trips = trips.filter(price__gte=min_price)
        if max_price:
            trips = trips.filter(price__lte=max_price)
        if seats:
            trips = trips.filter(available_seats__gte=seats)

        trips = trips.order_by("date", "time")
        serializer = TripSerializer(trips, many=True)
        return Response(serializer.data)


class MyTripsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        trips = Trip.objects.filter(driver=request.user).order_by("date", "time")
        serializer = TripSerializer(trips, many=True)
        return Response(serializer.data)


class MyBookingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = (
            Booking.objects.filter(rider=request.user)
            .select_related("trip")
            .order_by("-created_at")
        )
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)


class TripDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_object(self, trip_id):
        return Trip.objects.filter(id=trip_id).first()

    def get(self, request, trip_id):
        trip = self.get_object(trip_id)
        if not trip:
            return Response({"detail": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(TripSerializer(trip).data)

    def put(self, request, trip_id):
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        trip = self.get_object(trip_id)
        if not trip:
            return Response({"detail": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)
        if trip.driver_id != request.user.id:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        serializer = TripSerializer(trip, data=request.data)
        if serializer.is_valid():
            serializer.save(driver=request.user)
            return Response(serializer.data)
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, trip_id):
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        trip = self.get_object(trip_id)
        if not trip:
            return Response({"detail": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)
        if trip.driver_id != request.user.id:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        serializer = TripSerializer(trip, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(driver=request.user)
            return Response(serializer.data)
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, trip_id):
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        trip = self.get_object(trip_id)
        if not trip:
            return Response({"detail": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)
        if trip.driver_id != request.user.id:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        trip.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BookTripView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, trip_id):
        try:
            seats_requested = int(request.data.get("seats", 1))
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid seats value."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if seats_requested <= 0:
            return Response(
                {"detail": "Seats must be at least 1."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            trip = Trip.objects.select_for_update().filter(id=trip_id).first()
            if not trip:
                return Response(
                    {"detail": "Trip not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if trip.driver_id == request.user.id:
                return Response(
                    {"detail": "Driver cannot book their own trip."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if Booking.objects.filter(trip=trip, rider=request.user).exists():
                return Response(
                    {"detail": "You have already joined this trip."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if trip.available_seats < seats_requested:
                return Response(
                    {"detail": "Not enough seats available."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            trip.available_seats -= seats_requested
            trip.save(update_fields=["available_seats"])

            booking = BookingSerializer(
                data={"seats": seats_requested},
            )
            if booking.is_valid():
                booking_obj = booking.save(trip=trip, rider=request.user)
            else:
                return Response(booking.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "Seats booked successfully.",
                "seats_booked": seats_requested,
                "remaining_seats": trip.available_seats,
                "trip": TripSerializer(trip).data,
                "booking": BookingSerializer(booking_obj).data,
            },
            status=status.HTTP_200_OK,
        )


class JoinTripView(BookTripView):
    pass


class CancelBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        with transaction.atomic():
            booking = Booking.objects.select_for_update().filter(id=booking_id).first()
            if not booking:
                return Response(
                    {"detail": "Booking not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if booking.rider_id != request.user.id:
                return Response(
                    {"detail": "Not allowed."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            trip = Trip.objects.select_for_update().filter(id=booking.trip_id).first()
            if not trip:
                return Response(
                    {"detail": "Trip not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            trip.available_seats += booking.seats
            trip.save(update_fields=["available_seats"])
            booking.delete()

        return Response(
            {
                "message": "Booking cancelled.",
                "restored_seats": trip.available_seats,
            },
            status=status.HTTP_200_OK,
        )
