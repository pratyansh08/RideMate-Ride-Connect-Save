from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from trips.models import Booking

from .models import Review
from .serializers import ReviewSerializer


def _recalculate_driver_rating(driver):
    if driver.rating_count > 0:
        driver.rating = round(driver.rating_sum / driver.rating_count, 2)
    else:
        driver.rating = 0.0
    driver.save(update_fields=["rating", "rating_sum", "rating_count"])


class CreateReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            trip = serializer.validated_data.get("trip")
            if trip.driver_id == request.user.id:
                return Response(
                    {"detail": "Driver cannot review their own trip."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not trip.is_completed:
                return Response(
                    {"detail": "You can review only after the trip is completed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if Review.objects.filter(trip=trip, reviewer=request.user).exists():
                return Response(
                    {"detail": "You have already reviewed this trip."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not Booking.objects.filter(trip=trip, rider=request.user).exists():
                return Response(
                    {"detail": "You can only review trips you booked."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            with transaction.atomic():
                review = serializer.save(reviewer=request.user)
                trip.driver.rating_count += 1
                trip.driver.rating_sum += int(review.rating)
                _recalculate_driver_rating(trip.driver)
            return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ReviewListByTripView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, trip_id):
        reviews = Review.objects.filter(trip_id=trip_id).order_by("-created_at")
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)


class ReviewListByUserView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        reviews = Review.objects.filter(trip__driver_id=user_id).order_by("-created_at")
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)


class ReviewDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, review_id):
        return Review.objects.filter(id=review_id).first()

    def put(self, request, review_id):
        review = self.get_object(review_id)
        if not review:
            return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)
        if review.reviewer_id != request.user.id:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ReviewSerializer(review, data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                old_rating = review.rating
                updated = serializer.save(reviewer=request.user)
                diff = int(updated.rating) - int(old_rating)
                if diff != 0:
                    review.trip.driver.rating_sum += diff
                    _recalculate_driver_rating(review.trip.driver)
            return Response(ReviewSerializer(updated).data)
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, review_id):
        review = self.get_object(review_id)
        if not review:
            return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)
        if review.reviewer_id != request.user.id:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ReviewSerializer(review, data=request.data, partial=True)
        if serializer.is_valid():
            with transaction.atomic():
                old_rating = review.rating
                updated = serializer.save(reviewer=request.user)
                diff = int(updated.rating) - int(old_rating)
                if diff != 0:
                    review.trip.driver.rating_sum += diff
                    _recalculate_driver_rating(review.trip.driver)
            return Response(ReviewSerializer(updated).data)
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, review_id):
        review = self.get_object(review_id)
        if not review:
            return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)
        if review.reviewer_id != request.user.id:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        with transaction.atomic():
            driver = review.trip.driver
            driver.rating_count = max(driver.rating_count - 1, 0)
            driver.rating_sum = max(driver.rating_sum - int(review.rating), 0)
            review.delete()
            _recalculate_driver_rating(driver)
        return Response(status=status.HTTP_204_NO_CONTENT)
