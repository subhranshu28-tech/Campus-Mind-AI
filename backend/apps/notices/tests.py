from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import College, User
from .models import CampusEvent, Notice


class NoticesAndEventsTests(TestCase):
    def setUp(self):
        self.college_a = College.objects.create(name="Alpha", code="ALPHA", slug="alpha")
        self.college_b = College.objects.create(name="Beta", code="BETA", slug="beta")
        self.manager = User.objects.create_user(
            username="alpha-manager", email="m@example.test", password="SafePass123!",
            role="college_admin", college=self.college_a,
        )
        self.student = User.objects.create_user(
            username="alpha-student", email="s@example.test", password="SafePass123!",
            role="student", college=self.college_a,
        )
        self.other_manager = User.objects.create_user(
            username="beta-manager", email="bm@example.test", password="SafePass123!",
            role="college_admin", college=self.college_b,
        )
        self.client = APIClient()

    def test_manager_creates_notice_scoped_to_college(self):
        self.client.force_authenticate(self.manager)
        response = self.client.post("/api/notices/", {
            "title": "Exam week", "body": "Prepare well.", "audience": "students",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        notice = Notice.objects.get(pk=response.data["id"])
        self.assertEqual(notice.college_id, self.college_a.id)

    def test_students_cannot_create_notices(self):
        self.client.force_authenticate(self.student)
        response = self.client.post("/api/notices/", {
            "title": "Hack", "body": "no", "audience": "all",
        }, format="json")
        self.assertEqual(response.status_code, 403)

    def test_cross_college_isolation(self):
        Notice.objects.create(college=self.college_b, title="Beta notice", body="x")
        self.client.force_authenticate(self.manager)
        response = self.client.get("/api/notices/")
        self.assertEqual(response.status_code, 200)
        rows = response.data.get("results", response.data)
        self.assertEqual(rows, [])

    def test_event_requires_end_after_start(self):
        self.client.force_authenticate(self.manager)
        now = timezone.now()
        response = self.client.post("/api/events/", {
            "title": "Orientation", "starts_at": now.isoformat(),
            "ends_at": now.isoformat(), "audience": "all",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("ends_at", response.data)

    def test_expired_notices_are_hidden(self):
        past = timezone.now() - timezone.timedelta(days=2)
        Notice.objects.create(
            college=self.college_a, title="Old", body="x",
            published_at=past, expires_at=past + timezone.timedelta(hours=1),
        )
        self.client.force_authenticate(self.student)
        response = self.client.get("/api/notices/")
        rows = response.data.get("results", response.data)
        self.assertEqual(rows, [])
