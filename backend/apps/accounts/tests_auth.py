from django.test import TestCase
from rest_framework.test import APIClient

from .models import College, User


class AuthLifecycleTests(TestCase):
    def setUp(self):
        self.college = College.objects.create(name="Auth College", code="AUTH", slug="auth")
        self.user = User.objects.create_user(
            username="auth-user", email="auth@example.test", password="StrongPass123!",
            role=User.Role.COLLEGE_ADMIN, college=self.college,
        )
        self.client = APIClient()

    def _login(self):
        response = self.client.post(
            "/api/auth/token/",
            {"username": "auth-user", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_inactive_college_cannot_log_in(self):
        self.college.is_active = False
        self.college.save(update_fields=["is_active"])
        response = self.client.post(
            "/api/auth/token/",
            {"username": "auth-user", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("inactive", str(response.data).lower())

    def test_logout_blacklists_the_refresh_token(self):
        tokens = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        logout = self.client.post(
            "/api/auth/logout/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(logout.status_code, 200, logout.data)
        replay = APIClient().post(
            "/api/auth/token/refresh/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(replay.status_code, 401, replay.data)

    def test_health_check_reports_database_status(self):
        response = APIClient().get("/healthz/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})
