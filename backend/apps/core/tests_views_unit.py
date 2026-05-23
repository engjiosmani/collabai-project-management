from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

from apps.core.views import (
    HealthView,
    MetricsView,
    ForgotPasswordView,
    ResetPasswordView,
    TokenRefreshView,
    LogoutView,
)
from apps.user_profiles.models import PasswordResetToken

User = get_user_model()


class CoreViewsUnitTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_token_refresh_requires_refresh_field(self):
        request = self.factory.post("/api/v1/auth/refresh", {}, format="json")
        response = TokenRefreshView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("refresh", response.data)

    @patch("apps.core.views.api.RefreshToken")
    def test_token_refresh_returns_access_token(self, refresh_token_cls):
        token = MagicMock()
        token.access_token = "new-access-token"
        refresh_token_cls.return_value = token

        request = self.factory.post(
            "/api/v1/auth/refresh",
            {"refresh": "valid-refresh"},
            format="json",
        )
        response = TokenRefreshView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["access"], "new-access-token")

    @patch("apps.core.views.api.RefreshToken")
    def test_token_refresh_handles_invalid_token(self, refresh_token_cls):
        refresh_token_cls.side_effect = Exception("bad token")

        request = self.factory.post(
            "/api/v1/auth/refresh",
            {"refresh": "bad-refresh"},
            format="json",
        )

        with patch("apps.core.views.api.TokenError", Exception):
            response = TokenRefreshView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_requires_refresh_field(self):
        user = User.objects.create_user(
            username="logout_user",
            email="logout@example.com",
            password="password123",
        )
        request = self.factory.post("/api/v1/auth/logout", {}, format="json")
        force_authenticate(request, user=user)

        response = LogoutView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("refresh", response.data)

    @patch("apps.core.views.api.RefreshToken")
    def test_logout_blacklists_refresh_token(self, refresh_token_cls):
        user = User.objects.create_user(
            username="logout_success",
            email="logout_success@example.com",
            password="password123",
        )
        token = MagicMock()
        refresh_token_cls.return_value = token

        request = self.factory.post(
            "/api/v1/auth/logout",
            {"refresh": "valid-refresh"},
            format="json",
        )
        force_authenticate(request, user=user)

        response = LogoutView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        token.blacklist.assert_called_once()

    @patch("apps.core.views.api.RefreshToken")
    def test_logout_handles_invalid_refresh_token(self, refresh_token_cls):
        user = User.objects.create_user(
            username="logout_invalid",
            email="logout_invalid@example.com",
            password="password123",
        )
        refresh_token_cls.side_effect = Exception("bad token")

        request = self.factory.post(
            "/api/v1/auth/logout",
            {"refresh": "bad-refresh"},
            format="json",
        )
        force_authenticate(request, user=user)

        with patch("apps.core.views.api.TokenError", Exception):
            response = LogoutView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Invalid or expired refresh token.")

    @override_settings(RAG_FORCE_MEMORY_STORE=True, REDIS_AVAILABLE=False)
    @patch("apps.core.views.api.cache")
    @patch("apps.core.views.api.connection")
    @patch("apps.ai_assistant.services.groq_client.GroqClient")
    def test_health_view_ok_with_memory_vector_store(
        self,
        groq_client_cls,
        connection,
        cache,
    ):
        cursor_cm = MagicMock()
        cursor = MagicMock()
        cursor_cm.__enter__.return_value = cursor
        connection.cursor.return_value = cursor_cm

        groq_client_cls.return_value.is_configured.return_value = True
        cache.get.return_value = "1"

        request = self.factory.get("/api/v1/health/")
        response = HealthView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ok")
        self.assertEqual(response.data["database"], "ok")
        self.assertEqual(response.data["cache"], "locmem")
        self.assertEqual(response.data["vector_store"], "memory")
        self.assertTrue(response.data["groq_configured"])

    @override_settings(RAG_FORCE_MEMORY_STORE=False, REDIS_AVAILABLE=True)
    @patch("apps.core.views.api.cache")
    @patch("apps.core.views.api.connection")
    @patch("apps.ai_assistant.services.groq_client.GroqClient")
    def test_health_view_reports_degraded_when_database_fails(
        self,
        groq_client_cls,
        connection,
        cache,
    ):
        connection.cursor.side_effect = Exception("db down")
        groq_client_cls.return_value.is_configured.return_value = False
        cache.get.return_value = None

        request = self.factory.get("/api/v1/health/")
        response = HealthView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["status"], "degraded")
        self.assertEqual(response.data["database"], "unavailable")
        self.assertEqual(response.data["cache"], "redis")
        self.assertEqual(response.data["vector_store"], "redis")

    @patch("apps.core.views.api.get_cached_payload")
    @patch("apps.core.views.api.set_cached_payload")
    def test_metrics_view_returns_cached_payload(self, set_cached_payload, get_cached_payload):
        admin = User.objects.create_superuser(
            username="admin_cached",
            email="admin_cached@example.com",
            password="password123",
        )
        get_cached_payload.return_value = {"users": 123}

        request = self.factory.get("/api/v1/metrics/")
        force_authenticate(request, user=admin)

        response = MetricsView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"users": 123})
        set_cached_payload.assert_not_called()

    @patch("apps.core.views.api.get_cached_payload")
    @patch("apps.core.views.api.set_cached_payload")
    def test_metrics_view_builds_and_caches_payload(self, set_cached_payload, get_cached_payload):
        admin = User.objects.create_superuser(
            username="admin_metrics",
            email="admin_metrics@example.com",
            password="password123",
        )
        get_cached_payload.return_value = None

        request = self.factory.get("/api/v1/metrics/")
        force_authenticate(request, user=admin)

        response = MetricsView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("users", response.data)
        self.assertIn("organizations", response.data)
        set_cached_payload.assert_called_once()

    @patch("apps.core.tasks.send_password_reset_email.delay")
    def test_forgot_password_existing_user_creates_token_and_queues_email(self, delay):
        user = User.objects.create_user(
            username="forgot_user",
            email="forgot@example.com",
            password="password123",
        )

        request = self.factory.post(
            "/api/v1/auth/forgot-password",
            {"email": " FORGOT@example.com "},
            format="json",
        )
        response = ForgotPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PasswordResetToken.objects.filter(user=user).exists())
        delay.assert_called_once()

    @patch("apps.core.tasks.send_password_reset_email.delay")
    def test_forgot_password_unknown_user_still_returns_200(self, delay):
        request = self.factory.post(
            "/api/v1/auth/forgot-password",
            {"email": "missing@example.com"},
            format="json",
        )
        response = ForgotPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        delay.assert_not_called()

    def test_reset_password_rejects_invalid_token(self):
        request = self.factory.post(
            "/api/v1/auth/reset-password",
            {
                "token": "not-a-token",
                "new_password": "new-password-123",
                "confirm_password": "new-password-123",
            },
            format="json",
        )

        response = ResetPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Invalid or expired token.")

    def test_reset_password_rejects_used_token(self):
        user = User.objects.create_user(
            username="used_token",
            email="used@example.com",
            password="old-password",
        )
        token = PasswordResetToken.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=1),
            is_used=True,
        )

        request = self.factory.post(
            "/api/v1/auth/reset-password",
            {
                "token": str(token.token),
                "new_password": "new-password-123",
                "confirm_password": "new-password-123",
            },
            format="json",
        )

        response = ResetPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Token already used.")

    def test_reset_password_rejects_expired_token(self):
        user = User.objects.create_user(
            username="expired_token",
            email="expired@example.com",
            password="old-password",
        )
        token = PasswordResetToken.objects.create(
            user=user,
            expires_at=timezone.now() - timedelta(hours=1),
        )

        request = self.factory.post(
            "/api/v1/auth/reset-password",
            {
                "token": str(token.token),
                "new_password": "new-password-123",
                "confirm_password": "new-password-123",
            },
            format="json",
        )

        response = ResetPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Token has expired.")
    def test_reset_password_rejects_invalid_token(self):
        request = self.factory.post(
            "/api/v1/auth/reset-password",
            {
                "token": "00000000-0000-0000-0000-000000000000",
                "new_password": "new-password-123",
                "confirm_password": "new-password-123",
            },
            format="json",
        )

        response = ResetPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Invalid or expired token.")