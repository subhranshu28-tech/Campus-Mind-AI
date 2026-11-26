import re

from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import College, User


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PASSWORD_RESET_URL="http://testserver/password-reset",
)
class PasswordResetFlowTests(TestCase):
    def setUp(self):
        self.college = College.objects.create(name="Reset College", code="RESET", slug="reset")
        self.user = User.objects.create_user(
            username="reset-user",
            email="reset@example.test",
            password="OldStrongPass123!",
            college=self.college,
        )
        self.client = APIClient()

    def _request_reset(self):
        response = self.client.post(
            "/api/auth/password-reset/", {"email": self.user.email}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        match = re.search(r"uid=([^&\s]+)&token=([^\s]+)", body)
        self.assertIsNotNone(match, body)
        return match.group(1), match.group(2)

    def test_reset_link_changes_the_password(self):
        uid, token = self._request_reset()
        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"uid": uid, "token": token, "new_password": "NewStrongPass456!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPass456!"))

        login = self.client.post(
            "/api/auth/token/",
            {"username": self.user.username, "password": "NewStrongPass456!"},
            format="json",
        )
        self.assertEqual(login.status_code, 200, login.data)

    def test_invalid_token_returns_400_not_500(self):
        uid, _ = self._request_reset()
        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"uid": uid, "token": "not-a-real-token", "new_password": "NewStrongPass456!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)

    def test_weak_password_is_rejected_with_field_error(self):
        uid, token = self._request_reset()
        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"uid": uid, "token": token, "new_password": "password123"},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("new_password", response.data)
