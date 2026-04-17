from django.urls import path

from .views import ChatbotView, SendMessageView, TripMessagesView

urlpatterns = [
    path("chat/send/", SendMessageView.as_view()),
    path("chat/trip/<int:trip_id>/", TripMessagesView.as_view()),
    path("chatbot/", ChatbotView.as_view()),
]
