from django.urls import path

from .views import (
    BookTripView,
    CancelBookingView,
    CreateTripView,
    JoinTripView,
    MyBookingsView,
    MyTripsView,
    TripSearchView,
    TripDetailView,
    TripListView,
)

urlpatterns = [
    path("create/", CreateTripView.as_view()),
    path("list/", TripListView.as_view()),
    path("search/", TripSearchView.as_view()),
    path("my/", MyTripsView.as_view()),
    path("my-bookings/", MyBookingsView.as_view()),
    path("<int:trip_id>/", TripDetailView.as_view()),
    path("join/<int:trip_id>/", JoinTripView.as_view()),
    path("<int:trip_id>/book/", BookTripView.as_view()),
    path("bookings/<int:booking_id>/cancel/", CancelBookingView.as_view()),
]
