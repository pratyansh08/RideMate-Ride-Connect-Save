from django.urls import path

from .views import SendMessageView, TripMessagesView

urlpatterns = [
    path("send/", SendMessageView.as_view()),
    path("trip/<int:trip_id>/", TripMessagesView.as_view()),
]
