from django.urls import path
from .views import GoogleLoginView, ProfileView, ProtectedView, RegisterView, RequestRegistrationOTPView

urlpatterns = [
    path('protected/', ProtectedView.as_view()),
    path('me/', ProfileView.as_view()),
    path('request-otp/', RequestRegistrationOTPView.as_view()),
    path('register/', RegisterView.as_view()),
    path('google-login/', GoogleLoginView.as_view()),
]
