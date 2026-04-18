import os
import random
from datetime import timedelta

from django.core.mail import send_mail
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import RegistrationOTP, User
from .serializers import (
    GoogleLoginSerializer,
    OTPRequestSerializer,
    RegisterSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
)


# 🔒 JWT TEST / PROTECTED API
class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "message": "JWT token is working",
            "user": request.user.username
        })


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = UserProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response(UserProfileSerializer(request.user).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 📝 USER REGISTER (SIGNUP) API
class RegisterView(APIView):
    def post(self, request):
        otp_channel = (request.data.get("otp_channel") or "").strip().lower()
        otp_code = (request.data.get("otp_code") or "").strip()
        email = (request.data.get("email") or "").strip().lower()
        phone = (request.data.get("phone") or "").strip()

        if otp_channel not in {"email", "phone"}:
            return Response(
                {"errors": {"otp_channel": ["Choose OTP method: email or phone."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not otp_code:
            return Response(
                {"errors": {"otp_code": ["OTP is required."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp_target = email if otp_channel == "email" else phone
        if not otp_target:
            field = "email" if otp_channel == "email" else "phone"
            return Response(
                {"errors": {field: [f"{field.title()} is required for selected OTP method."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp_record = RegistrationOTP.objects.filter(
            channel=otp_channel,
            target=otp_target,
            code=otp_code,
            is_used=False,
            expires_at__gte=timezone.now(),
        ).order_by("-created_at").first()
        if not otp_record:
            return Response(
                {"errors": {"otp_code": ["Invalid or expired OTP."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            otp_record.is_used = True
            otp_record.save(update_fields=["is_used"])
            return Response(
                {"message": "User registered successfully"},
                status=status.HTTP_201_CREATED
            )
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class RequestRegistrationOTPView(APIView):
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        channel = serializer.validated_data["channel"]
        target = (
            serializer.validated_data["email"]
            if channel == "email"
            else serializer.validated_data["phone"]
        )

        code = f"{random.randint(0, 999999):06d}"
        otp = RegistrationOTP.objects.create(
            channel=channel,
            target=target,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        if channel == "email":
            self._send_email_otp(target, code)
            message = "OTP sent to email."
        else:
            # SMS gateway integration can replace this later.
            message = "OTP generated for phone verification."

        payload = {"message": message, "expires_in_seconds": 600}
        if settings.DEBUG:
            payload["debug_otp"] = otp.code
        return Response(payload, status=status.HTTP_200_OK)

    def _send_email_otp(self, email, code):
        subject = "RideMate Registration OTP"
        body = f"Your RideMate OTP is {code}. It is valid for 10 minutes."
        send_mail(
            subject,
            body,
            getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@ridemate.local"),
            [email],
            fail_silently=True,
        )


class GoogleLoginView(APIView):
    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        allowed_client_ids = self._allowed_google_client_ids()
        if not allowed_client_ids:
            return Response(
                {"detail": "Google OAuth is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            google_user = id_token.verify_oauth2_token(
                serializer.validated_data["token"],
                google_requests.Request(),
                None,
                clock_skew_in_seconds=30,
            )
        except ValueError as exc:
            detail = "Invalid Google token."
            if settings.DEBUG:
                detail = f"Invalid Google token: {exc}"
            return Response(
                {"detail": detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        issuer = (google_user.get("iss") or "").strip()
        if issuer not in {"accounts.google.com", "https://accounts.google.com"}:
            return Response(
                {"detail": "Invalid Google token issuer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        audience = (google_user.get("aud") or "").strip()
        if audience not in allowed_client_ids:
            return Response(
                {"detail": "Google token audience mismatch. Check client ID configuration."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = (google_user.get("email") or "").strip().lower()
        if not email:
            return Response(
                {"detail": "Google account email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            user = self._create_google_user(google_user, email)

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
            },
            status=status.HTTP_200_OK,
        )

    def _create_google_user(self, google_user, email):
        base_username = (
            google_user.get("name")
            or email.split("@")[0]
            or "ridemate_user"
        )
        normalized_username = "".join(
            character if character.isalnum() or character in {"_", "."} else "_"
            for character in base_username.strip().lower()
        ).strip("._")
        normalized_username = normalized_username or "ridemate_user"

        username = normalized_username[:150]
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix_text = str(suffix)
            username = f"{normalized_username[: max(1, 150 - len(suffix_text) - 1)]}_{suffix_text}"
            suffix += 1

        return User.objects.create_user(
            username=username,
            email=email,
            gender=(google_user.get("gender") or "")[:10] or None,
        )

    def _allowed_google_client_ids(self):
        # Support both a single client ID and comma-separated multiple IDs.
        raw_values = [
            os.getenv("GOOGLE_OAUTH_CLIENT_ID", ""),
            os.getenv("GOOGLE_OAUTH_CLIENT_IDS", ""),
        ]
        ids = set()
        for raw in raw_values:
            for value in raw.split(","):
                cleaned = value.strip()
                if cleaned:
                    ids.add(cleaned)
        return ids
