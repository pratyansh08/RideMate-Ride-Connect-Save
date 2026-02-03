from django.urls import path
from .views import ProtectedView, RegisterView

urlpatterns = [
    path('protected/', ProtectedView.as_view()),
    path('register/', RegisterView.as_view()),
]
