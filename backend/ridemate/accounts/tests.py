from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(
    SECRET_KEY="test-secret",
)
class GoogleLoginViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.google_client_id = "test-google-client-id.apps.googleusercontent.com"
        self.env_patcher = patch.dict(
            "os.environ",
            {"GOOGLE_OAUTH_CLIENT_ID": self.google_client_id},
            clear=False,
        )
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    @patch("accounts.views.id_token.verify_oauth2_token")
    def test_google_login_creates_user_and_returns_jwt(self, mocked_verify):
        mocked_verify.return_value = {
            "email": "shreya@example.com",
            "name": "Shreya Singh",
            "aud": self.google_client_id,
            "iss": "https://accounts.google.com",
        }

        response = self.client.post(
            "/api/accounts/google-login/",
            {"token": "google-id-token"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        created_user = get_user_model().objects.get(email="shreya@example.com")
        self.assertTrue(created_user.username.startswith("shreya_singh"))
        mocked_verify.assert_called_once()

    @patch("accounts.views.id_token.verify_oauth2_token")
    def test_google_login_reuses_existing_user(self, mocked_verify):
        user_model = get_user_model()
        existing_user = user_model.objects.create_user(
            username="existing_user",
            email="shreya@example.com",
            password="secret123",
        )
        mocked_verify.return_value = {
            "email": "shreya@example.com",
            "name": "Shreya Singh",
            "aud": self.google_client_id,
            "iss": "https://accounts.google.com",
        }

        response = self.client.post(
            "/api/accounts/google-login/",
            {"token": "google-id-token"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["id"], existing_user.id)
        self.assertEqual(user_model.objects.filter(email="shreya@example.com").count(), 1)

    @patch("accounts.views.id_token.verify_oauth2_token", side_effect=ValueError("bad token"))
    def test_google_login_rejects_invalid_token(self, mocked_verify):
        response = self.client.post(
            "/api/accounts/google-login/",
            {"token": "bad-token"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid Google token", response.data["detail"])
        mocked_verify.assert_called_once()


@override_settings(
    SECRET_KEY="test-secret",
)
class ProfileViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="profile_user",
            email="profile@example.com",
            password="secret123",
            gender="male",
        )

    def test_profile_requires_authentication(self):
        response = self.client.get("/api/accounts/me/")
        self.assertEqual(response.status_code, 401)

    def test_profile_returns_logged_in_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/accounts/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "profile_user")
        self.assertEqual(response.data["email"], "profile@example.com")

    def test_profile_allows_updating_phone_and_gender(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            "/api/accounts/me/",
            {"phone": "9999999999", "gender": "female"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "9999999999")
        self.assertEqual(self.user.gender, "female")

    def test_profile_rejects_duplicate_phone(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="existing_phone_user",
            email="existing_phone@example.com",
            password="secret123",
            phone="8888888888",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            "/api/accounts/me/",
            {"phone": "8888888888"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", response.data)


@override_settings(
    SECRET_KEY="test-secret",
    DEBUG=True,
)
class RegistrationOTPFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_request_otp_returns_debug_code_in_debug_mode(self):
        response = self.client.post(
            "/api/accounts/request-otp/",
            {"channel": "email", "email": "otp@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("debug_otp", response.data)

    def test_register_requires_valid_otp(self):
        response = self.client.post(
            "/api/accounts/register/",
            {
                "username": "otp_user",
                "email": "otpuser@example.com",
                "password": "Secret123!",
                "otp_channel": "email",
                "otp_code": "123456",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("otp_code", response.data["errors"])

    def test_register_success_with_valid_otp(self):
        otp_response = self.client.post(
            "/api/accounts/request-otp/",
            {"channel": "email", "email": "new@example.com"},
            format="json",
        )
        otp_code = otp_response.data["debug_otp"]

        response = self.client.post(
            "/api/accounts/register/",
            {
                "username": "new_user",
                "email": "new@example.com",
                "password": "Secret123!",
                "otp_channel": "email",
                "otp_code": otp_code,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(get_user_model().objects.filter(email="new@example.com").exists())
