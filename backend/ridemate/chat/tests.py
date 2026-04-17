from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from trips.models import Booking, Trip

from .ai_service import GeminiServiceError, extract_trip_details


class ChatbotViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.driver = get_user_model().objects.create_user(
            username="driver1",
            password="secret123",
        )
        self.rider = get_user_model().objects.create_user(
            username="rider1",
            password="secret123",
        )
        self.pune_trip = Trip.objects.create(
            source="Pune",
            destination="Mumbai",
            date="2099-01-05",
            time="09:00",
            available_seats=3,
            price="450.00",
            driver=self.driver,
        )
        self.alt_pune_trip = Trip.objects.create(
            source="Pune",
            destination="Mumbai",
            date="2099-01-05",
            time="07:30",
            available_seats=1,
            price="520.00",
            driver=self.driver,
        )
        self.booking = Booking.objects.create(
            trip=self.pune_trip,
            rider=self.rider,
            seats=1,
        )

    def test_cancel_message_skips_ai_and_returns_static_reply(self):
        response = self.client.post("/api/chatbot/", {"message": "cancel"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["rides"], [])
        self.assertEqual(response.data["bookings"], [])
        self.assertIn("canceled", response.data["reply"].lower())

    @patch("chat.views.generate_chatbot_reply", return_value="Here is the best ride for you.")
    @patch(
        "chat.views.extract_trip_details",
        return_value={
            "source": "Pune",
            "destination": "Mumbai",
            "date": "2099-01-05",
            "intent": "find_ride",
            "follow_up_question": None,
            "seats_needed": 2,
            "max_price": 500,
            "time_preference": "morning",
            "sort_by": "cheapest",
            "booking_reference": None,
            "ride_reference": None,
        },
    )
    def test_chatbot_returns_filtered_rides_and_recommendations(self, mocked_extract, mocked_reply):
        response = self.client.post(
            "/api/chatbot/",
            {"message": "Need 2 morning seats from Pune to Mumbai under 500"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reply"], "Here is the best ride for you.")
        self.assertEqual(len(response.data["rides"]), 1)
        self.assertEqual(response.data["rides"][0]["id"], self.pune_trip.id)
        self.assertEqual(response.data["recommendations"]["cheapest"], self.pune_trip.id)
        self.assertIn("Show earliest ride", response.data["suggestions"])
        mocked_extract.assert_called_once()
        mocked_reply.assert_called_once()

    @patch("chat.views.generate_chatbot_reply", return_value="You have one active booking.")
    @patch(
        "chat.views.extract_trip_details",
        return_value={
            "source": None,
            "destination": None,
            "date": None,
            "intent": "my_bookings",
            "follow_up_question": None,
            "seats_needed": None,
            "max_price": None,
            "time_preference": None,
            "sort_by": None,
            "booking_reference": None,
            "ride_reference": None,
        },
    )
    def test_chatbot_returns_authenticated_bookings(self, mocked_extract, mocked_reply):
        self.client.force_authenticate(user=self.rider)
        response = self.client.post("/api/chatbot/", {"message": "show my bookings"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reply"], "You have one active booking.")
        self.assertEqual(len(response.data["bookings"]), 1)
        self.assertEqual(response.data["bookings"][0]["id"], self.booking.id)
        self.assertEqual(response.data["bookings"][0]["trip_details"]["source"], "Pune")
        self.assertEqual(response.data["bookings"][0]["trip_details"]["destination"], "Mumbai")
        mocked_extract.assert_called_once()
        mocked_reply.assert_called_once()

    def test_chatbot_cancel_booking_removes_booking_and_restores_seats(self):
        self.client.force_authenticate(user=self.rider)
        with patch(
            "chat.views.extract_trip_details",
            return_value={
                "source": None,
                "destination": None,
                "date": None,
                "intent": "cancel_booking",
                "follow_up_question": None,
                "seats_needed": None,
                "max_price": None,
                "time_preference": None,
                "sort_by": None,
                "booking_reference": self.booking.id,
                "ride_reference": None,
            },
        ) as mocked_extract, patch(
            "chat.views.generate_chatbot_reply",
            side_effect=GeminiServiceError("Gemini is down."),
        ) as mocked_reply:
            response = self.client.post(
                "/api/chatbot/",
                {"message": f"cancel booking {self.booking.id}"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["bookings"], [])
        self.assertIn("canceled", response.data["reply"].lower())
        self.pune_trip.refresh_from_db()
        self.assertEqual(self.pune_trip.available_seats, 4)
        self.assertFalse(Booking.objects.filter(id=self.booking.id).exists())
        mocked_extract.assert_called_once()
        mocked_reply.assert_called_once()

    def test_chatbot_books_ride_by_text_and_returns_updated_bookings(self):
        self.client.force_authenticate(user=self.rider)
        with patch(
            "chat.views.extract_trip_details",
            return_value={
                "source": "Pune",
                "destination": "Mumbai",
                "date": "2099-01-05",
                "intent": "book_ride",
                "follow_up_question": None,
                "seats_needed": 1,
                "max_price": None,
                "time_preference": None,
                "sort_by": "earliest",
                "booking_reference": None,
                "ride_reference": None,
            },
        ) as mocked_extract, patch(
            "chat.views.generate_chatbot_reply",
            side_effect=GeminiServiceError("Gemini is down."),
        ) as mocked_reply:
            response = self.client.post(
                "/api/chatbot/",
                {"message": "book earliest ride from Pune to Mumbai"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("booked", response.data["reply"].lower())
        self.alt_pune_trip.refresh_from_db()
        self.assertEqual(self.alt_pune_trip.available_seats, 0)
        self.assertEqual(Booking.objects.filter(rider=self.rider).count(), 2)
        self.assertEqual(len(response.data["bookings"]), 2)
        mocked_extract.assert_called_once()
        mocked_reply.assert_called_once()


class ExtractTripDetailsTests(TestCase):
    @patch("chat.ai_service.call_gemini", side_effect=GeminiServiceError("Gemini offline"))
    def test_extract_trip_details_merges_follow_up_with_history(self, mocked_call):
        details = extract_trip_details(
            "under 500 for 2 seats",
            history=[
                {"role": "user", "text": "Find me a ride from Pune to Mumbai tomorrow"},
                {"role": "bot", "text": "Sure, I can help with that."},
            ],
        )

        self.assertEqual(details["source"], "Pune")
        self.assertEqual(details["destination"], "Mumbai")
        self.assertEqual(details["intent"], "find_ride")
        self.assertEqual(details["max_price"], 500.0)
        self.assertEqual(details["seats_needed"], 2)
        mocked_call.assert_called_once()
