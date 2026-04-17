from datetime import date, time

from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from trips.models import Booking, Trip
from trips.serializers import BookingSerializer, TripSerializer

from .ai_service import (
    GeminiServiceError,
    build_fallback_reply,
    extract_trip_details,
    generate_chatbot_reply,
)
from .models import Message
from .serializers import MessageSerializer


def _is_trip_member(user, trip_id):
    trip = Trip.objects.filter(id=trip_id).first()
    if not trip:
        return None, False
    if trip.driver_id == user.id:
        return trip, True
    if Booking.objects.filter(trip_id=trip_id, rider_id=user.id).exists():
        return trip, True
    return trip, False


class SendMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        trip_id = request.data.get("trip")
        trip, is_member = _is_trip_member(request.user, trip_id)
        if not trip:
            return Response({"detail": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)
        if not is_member:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        serializer = MessageSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            message = serializer.save(sender=request.user)
            return Response(
                MessageSerializer(message, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class TripMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):
        trip, is_member = _is_trip_member(request.user, trip_id)
        if not trip:
            return Response({"detail": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)
        if not is_member:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        try:
            limit = int(request.query_params.get("limit", 50))
            offset = int(request.query_params.get("offset", 0))
        except ValueError:
            return Response({"detail": "Invalid pagination parameters."}, status=status.HTTP_400_BAD_REQUEST)

        limit = max(1, min(limit, 200))
        offset = max(0, offset)

        qs = Message.objects.filter(trip_id=trip_id).order_by("created_at")
        messages = qs[offset : offset + limit]
        serializer = MessageSerializer(messages, many=True, context={"request": request})
        return Response(serializer.data)


class ChatbotView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        message = str(request.data.get("message", "")).strip()
        history = self._sanitize_history(request.data.get("history"))
        if not message:
            return Response(
                {"detail": "Message is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if message.lower() == "cancel":
            return Response(
                {
                    "reply": (
                        "Okay, I canceled that request. "
                        "Share your source and destination whenever you want to search again."
                    ),
                    "rides": [],
                    "bookings": [],
                    "recommendations": {},
                    "suggestions": ["Find me a ride", "Show my bookings"],
                    "context": {},
                },
                status=status.HTTP_200_OK,
            )

        extracted_details = extract_trip_details(message, history=history)

        if extracted_details.get("intent") == "my_bookings":
            return self._handle_my_bookings(request, message, history, extracted_details)

        if extracted_details.get("intent") == "cancel_booking":
            return self._handle_cancel_booking(request, message, history, extracted_details)

        if extracted_details.get("intent") == "book_ride":
            return self._handle_book_ride(request, message, history, extracted_details)

        rides = self._find_matching_rides(extracted_details)
        recommendations = self._build_recommendations(rides)
        suggestions = self._build_suggestions(
            extracted_details=extracted_details,
            rides=rides,
            bookings=[],
            is_authenticated=request.user.is_authenticated,
        )

        try:
            reply = generate_chatbot_reply(
                user_message=message,
                extracted_details=extracted_details,
                rides=rides,
                bookings=[],
                history=history,
                recommendations=recommendations,
            )
        except GeminiServiceError:
            reply = build_fallback_reply(
                user_message=message,
                extracted_details=extracted_details,
                rides=rides,
                bookings=[],
                recommendations=recommendations,
            )

        return Response(
            {
                "reply": reply,
                "rides": rides,
                "bookings": [],
                "recommendations": recommendations,
                "suggestions": suggestions,
                "context": extracted_details,
            },
            status=status.HTTP_200_OK,
        )

    def _handle_my_bookings(self, request, message, history, extracted_details):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {
                    "reply": "Please login first, then I can show your bookings here.",
                    "rides": [],
                    "bookings": [],
                    "recommendations": {},
                    "suggestions": ["Find me a ride", "Show cheap rides"],
                    "context": extracted_details,
                },
                status=status.HTTP_200_OK,
            )

        bookings = self._serialize_bookings(self._get_user_bookings_queryset(request.user))
        suggestions = self._build_suggestions(
            extracted_details=extracted_details,
            rides=[],
            bookings=bookings,
            is_authenticated=True,
        )
        try:
            reply = generate_chatbot_reply(
                user_message=message,
                extracted_details=extracted_details,
                rides=[],
                bookings=bookings,
                history=history,
                recommendations={},
            )
        except GeminiServiceError:
            reply = build_fallback_reply(
                user_message=message,
                extracted_details=extracted_details,
                rides=[],
                bookings=bookings,
                recommendations={},
            )

        return Response(
            {
                "reply": reply,
                "rides": [],
                "bookings": bookings,
                "recommendations": {},
                "suggestions": suggestions,
                "context": extracted_details,
            },
            status=status.HTTP_200_OK,
        )

    def _handle_cancel_booking(self, request, message, history, extracted_details):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {
                    "reply": "Please login first, then I can cancel your booking.",
                    "rides": [],
                    "bookings": [],
                    "recommendations": {},
                    "suggestions": ["Show my bookings", "Find me a ride"],
                    "context": extracted_details,
                },
                status=status.HTTP_200_OK,
            )

        booking = self._resolve_booking_to_cancel(request.user, extracted_details)
        bookings_queryset = self._get_user_bookings_queryset(request.user)
        if not booking:
            bookings = self._serialize_bookings(bookings_queryset)
            return Response(
                {
                    "reply": (
                        "Tell me which booking to cancel, for example 'cancel booking 12'."
                        if bookings
                        else "You do not have any active bookings to cancel."
                    ),
                    "rides": [],
                    "bookings": bookings,
                    "recommendations": {},
                    "suggestions": self._build_suggestions(
                        extracted_details=extracted_details,
                        rides=[],
                        bookings=bookings,
                        is_authenticated=True,
                    ),
                    "context": extracted_details,
                },
                status=status.HTTP_200_OK,
            )

        action_result = self._cancel_booking_instance(request.user, booking.id)
        bookings = self._serialize_bookings(self._get_user_bookings_queryset(request.user))
        suggestions = self._build_suggestions(
            extracted_details=extracted_details,
            rides=[],
            bookings=bookings,
            is_authenticated=True,
        )
        try:
            reply = generate_chatbot_reply(
                user_message=message,
                extracted_details=extracted_details,
                rides=[],
                bookings=bookings,
                history=history,
                recommendations={},
                action_result=action_result,
            )
        except GeminiServiceError:
            reply = build_fallback_reply(
                user_message=message,
                extracted_details=extracted_details,
                rides=[],
                bookings=bookings,
                recommendations={},
                action_result=action_result,
            )

        return Response(
            {
                "reply": reply,
                "rides": [],
                "bookings": bookings,
                "recommendations": {},
                "suggestions": suggestions,
                "context": extracted_details,
            },
            status=status.HTTP_200_OK,
        )

    def _handle_book_ride(self, request, message, history, extracted_details):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {
                    "reply": "Please login first, then I can book the ride for you.",
                    "rides": [],
                    "bookings": [],
                    "recommendations": {},
                    "suggestions": ["Find me a ride", "Show my bookings"],
                    "context": extracted_details,
                },
                status=status.HTTP_200_OK,
            )

        trip = self._resolve_trip_to_book(extracted_details)
        if not trip:
            rides = self._find_matching_rides({**extracted_details, "intent": "book_ride"})
            return Response(
                {
                    "reply": (
                        "I could not find a specific ride to book. "
                        "Try 'book ride 12' or ask me to show matching rides first."
                    ),
                    "rides": rides,
                    "bookings": [],
                    "recommendations": self._build_recommendations(rides),
                    "suggestions": self._build_suggestions(
                        extracted_details=extracted_details,
                        rides=rides,
                        bookings=[],
                        is_authenticated=True,
                    ),
                    "context": extracted_details,
                },
                status=status.HTTP_200_OK,
            )

        seats_requested = extracted_details.get("seats_needed") or 1
        try:
            action_result = self._book_trip_instance(request.user, trip.id, seats_requested)
        except ValueError as exc:
            return Response(
                {
                    "reply": str(exc),
                    "rides": [TripSerializer(trip).data],
                    "bookings": self._serialize_bookings(self._get_user_bookings_queryset(request.user)),
                    "recommendations": {"cheapest": trip.id, "earliest": trip.id, "best_value": trip.id},
                    "suggestions": ["Show my bookings", "Find another ride"],
                    "context": extracted_details,
                },
                status=status.HTTP_200_OK,
            )
        bookings = self._serialize_bookings(self._get_user_bookings_queryset(request.user))
        suggestions = self._build_suggestions(
            extracted_details=extracted_details,
            rides=[],
            bookings=bookings,
            is_authenticated=True,
        )
        try:
            reply = generate_chatbot_reply(
                user_message=message,
                extracted_details=extracted_details,
                rides=[],
                bookings=bookings,
                history=history,
                recommendations={},
                action_result=action_result,
            )
        except GeminiServiceError:
            reply = build_fallback_reply(
                user_message=message,
                extracted_details=extracted_details,
                rides=[],
                bookings=bookings,
                recommendations={},
                action_result=action_result,
            )

        return Response(
            {
                "reply": reply,
                "rides": [],
                "bookings": bookings,
                "recommendations": {},
                "suggestions": suggestions,
                "context": extracted_details,
            },
            status=status.HTTP_200_OK,
        )

    def _sanitize_history(self, raw_history):
        cleaned = []
        if not isinstance(raw_history, list):
            return cleaned

        for entry in raw_history[-8:]:
            if not isinstance(entry, dict):
                continue
            text = str(entry.get("text", "")).strip()
            if not text:
                continue
            role = "user" if entry.get("role") == "user" else "bot"
            cleaned.append({"role": role, "text": text[:280]})
        return cleaned

    def _find_matching_rides(self, extracted_details):
        source = extracted_details.get("source")
        destination = extracted_details.get("destination")
        travel_date = extracted_details.get("date")
        intent = extracted_details.get("intent")
        seats_needed = extracted_details.get("seats_needed")
        max_price = extracted_details.get("max_price")
        time_preference = extracted_details.get("time_preference")
        sort_by = extracted_details.get("sort_by") or "cheapest"

        if intent not in {"find_ride", "general", "book_ride"}:
            return []
        if not source and not destination:
            return []

        trips = Trip.objects.filter(is_completed=False, available_seats__gt=0)
        if travel_date:
            trips = trips.filter(date=travel_date)
        else:
            trips = trips.filter(date__gte=date.today())

        if source:
            trips = trips.filter(source__icontains=source)
        if destination:
            trips = trips.filter(destination__icontains=destination)
        if seats_needed:
            trips = trips.filter(available_seats__gte=seats_needed)
        if max_price:
            trips = trips.filter(price__lte=max_price)

        if time_preference == "morning":
            trips = trips.filter(time__gte=time(5, 0), time__lt=time(12, 0))
        elif time_preference == "afternoon":
            trips = trips.filter(time__gte=time(12, 0), time__lt=time(17, 0))
        elif time_preference == "evening":
            trips = trips.filter(time__gte=time(17, 0), time__lt=time(21, 0))
        elif time_preference == "night":
            trips = trips.filter(Q(time__gte=time(21, 0)) | Q(time__lt=time(5, 0)))

        if sort_by == "earliest":
            trips = trips.order_by("date", "time", "price")
        elif sort_by == "best_value":
            trips = trips.order_by("price", "-available_seats", "date", "time")
        else:
            trips = trips.order_by("price", "date", "time")

        return TripSerializer(trips[:6], many=True).data

    def _build_recommendations(self, rides):
        if not rides:
            return {}

        cheapest = min(rides, key=lambda ride: (float(ride["price"]), ride["date"], ride["time"]))
        earliest = min(rides, key=lambda ride: (ride["date"], ride["time"], float(ride["price"])))
        best_value = min(
            rides,
            key=lambda ride: (
                float(ride["price"]),
                -int(ride["available_seats"]),
                ride["date"],
                ride["time"],
            ),
        )
        return {
            "cheapest": cheapest["id"],
            "earliest": earliest["id"],
            "best_value": best_value["id"],
        }

    def _build_suggestions(self, extracted_details, rides, bookings, is_authenticated):
        suggestions = []
        if rides:
            if extracted_details.get("sort_by") != "cheapest":
                suggestions.append("Show cheapest ride")
            if extracted_details.get("sort_by") != "earliest":
                suggestions.append("Show earliest ride")
            if is_authenticated:
                suggestions.append("Book cheapest ride")
            if not extracted_details.get("time_preference"):
                suggestions.append("Tomorrow morning")
            if not extracted_details.get("seats_needed"):
                suggestions.append("2 seats")
            if not extracted_details.get("max_price"):
                cheapest_price = int(float(min(rides, key=lambda ride: float(ride["price"]))["price"]))
                suggestions.append(f"Under Rs {cheapest_price}")
            if is_authenticated:
                suggestions.append("Show my bookings")
        elif bookings:
            suggestions.append(f"Cancel booking {bookings[0]['id']}")
            suggestions.append("Find me a ride")
            if len(bookings) > 1:
                suggestions.append("Show my bookings")
        else:
            if extracted_details.get("intent") == "cancel_booking":
                suggestions.append("Show my bookings")
            suggestions.append("Find me a ride from Pune to Mumbai tomorrow")
            if is_authenticated:
                suggestions.append("Show my bookings")
            suggestions.append("Cheap rides tomorrow")

        unique = []
        for suggestion in suggestions:
            if suggestion not in unique:
                unique.append(suggestion)
        return unique[:4]

    def _get_user_bookings_queryset(self, user):
        return (
            Booking.objects.filter(rider=user)
            .select_related("trip", "trip__driver")
            .order_by("-created_at")
        )

    def _serialize_bookings(self, queryset):
        return BookingSerializer(queryset, many=True).data

    def _resolve_booking_to_cancel(self, user, extracted_details):
        bookings = self._get_user_bookings_queryset(user)
        booking_reference = extracted_details.get("booking_reference")
        source = extracted_details.get("source")
        destination = extracted_details.get("destination")

        if booking_reference:
            return bookings.filter(id=booking_reference).first()

        if source or destination:
            filtered = bookings
            if source:
                filtered = filtered.filter(trip__source__icontains=source)
            if destination:
                filtered = filtered.filter(trip__destination__icontains=destination)
            if filtered.count() == 1:
                return filtered.first()

        if bookings.count() == 1:
            return bookings.first()
        return None

    def _resolve_trip_to_book(self, extracted_details):
        ride_reference = extracted_details.get("ride_reference")
        if ride_reference:
            return (
                Trip.objects.filter(id=ride_reference, is_completed=False, available_seats__gt=0)
                .order_by("date", "time")
                .first()
            )

        rides = self._find_matching_rides({**extracted_details, "intent": "book_ride"})
        if not rides:
            return None

        recommendations = self._build_recommendations(rides)
        selected_ride_id = recommendations.get("best_value")
        if extracted_details.get("sort_by") == "earliest":
            selected_ride_id = recommendations.get("earliest")
        elif extracted_details.get("sort_by") == "cheapest" or not extracted_details.get("sort_by"):
            selected_ride_id = recommendations.get("cheapest")

        if not selected_ride_id:
            selected_ride_id = rides[0]["id"]
        return Trip.objects.filter(id=selected_ride_id, is_completed=False, available_seats__gt=0).first()

    def _cancel_booking_instance(self, user, booking_id):
        with transaction.atomic():
            booking = (
                Booking.objects.select_for_update()
                .select_related("trip")
                .filter(id=booking_id, rider=user)
                .first()
            )
            if not booking:
                raise ValueError("Booking not found.")

            trip = Trip.objects.select_for_update().filter(id=booking.trip_id).first()
            if not trip:
                raise ValueError("Trip not found.")

            trip.available_seats += booking.seats
            trip.save(update_fields=["available_seats"])

            route = f"{trip.source} to {trip.destination}"
            canceled_booking_id = booking.id
            booking.delete()

        return {
            "type": "cancel_booking",
            "booking_id": canceled_booking_id,
            "route": route,
        }

    def _book_trip_instance(self, user, trip_id, seats_requested):
        with transaction.atomic():
            trip = Trip.objects.select_for_update().filter(id=trip_id).first()
            if not trip:
                raise ValueError("Trip not found.")
            if trip.driver_id == user.id:
                raise ValueError("Driver cannot book their own trip.")
            if Booking.objects.filter(trip=trip, rider=user).exists():
                raise ValueError("You have already joined this trip.")
            if trip.available_seats < seats_requested:
                raise ValueError("Not enough seats available.")

            trip.available_seats -= seats_requested
            trip.save(update_fields=["available_seats"])

            booking = BookingSerializer(data={"seats": seats_requested})
            if not booking.is_valid():
                raise ValueError("Invalid seats requested.")
            booking.save(trip=trip, rider=user)

        return {
            "type": "book_ride",
            "trip_id": trip.id,
            "route": f"{trip.source} to {trip.destination}",
            "remaining_seats": trip.available_seats,
        }
