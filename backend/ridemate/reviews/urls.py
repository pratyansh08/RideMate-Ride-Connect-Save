from django.urls import path

from .views import (
    CreateReviewView,
    ReviewDetailView,
    ReviewListByTripView,
    ReviewListByUserView,
)

urlpatterns = [
    path("create/", CreateReviewView.as_view()),
    path("trip/<int:trip_id>/", ReviewListByTripView.as_view()),
    path("user/<int:user_id>/", ReviewListByUserView.as_view()),
    path("<int:review_id>/", ReviewDetailView.as_view()),
]
