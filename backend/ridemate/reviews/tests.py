from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from trips.models import Trip

from .models import Review


class ReviewSummaryViewTests(TestCase):
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
        self.trip = Trip.objects.create(
            source="Pune",
            destination="Mumbai",
            date="2099-01-05",
            time="09:00",
            available_seats=3,
            price="450.00",
            driver=self.driver,
        )
        Review.objects.create(
            trip=self.trip,
            reviewer=self.rider,
            rating=5,
            comment="Driver was punctual and the ride felt safe.",
        )

    @patch("reviews.ai_service.call_gemini", return_value="Reviews are strongly positive overall.")
    def test_review_summary_endpoint_returns_summary_and_stats(self, mocked_call):
        response = self.client.get(f"/api/reviews/trip/{self.trip.id}/summary/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"], "Reviews are strongly positive overall.")
        self.assertEqual(response.data["stats"]["count"], 1)
        self.assertEqual(response.data["stats"]["average_rating"], 5.0)
        mocked_call.assert_called_once()
