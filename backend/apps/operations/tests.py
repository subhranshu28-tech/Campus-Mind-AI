from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import College, User
from apps.campus.models import Classroom, Department, Faculty, Semester, TimetableEntry

from . import services
from .models import FacultyLeave, Notification, Substitution


class OperationsApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", password="Demo-pass-123", verbosity=0)
        cls.demo_college = College.objects.get(code="DEMO")
        cls.admin = User.objects.create_user(
            "boss", "boss@x.io", "Demo-pass-123", role="college_admin", college=cls.demo_college
        )
        cls.semester = Semester.objects.get()

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def _monday(self):
        today = date.today()
        return today + timedelta(days=(7 - today.weekday()) % 7 or 7)

    def test_leave_approval_assigns_conflict_free_cover_and_notifies(self):
        entry = TimetableEntry.objects.filter(faculty__employee_id="EMP001").order_by("weekday", "period").first()
        day = self._monday() + timedelta(days=entry.weekday)
        leave = FacultyLeave.objects.create(faculty=entry.faculty, start_date=day, end_date=day, reason="Conference")
        response = self.client.post(f"/api/leaves/{leave.id}/approve/")
        self.assertEqual(response.status_code, 200)
        covers = Substitution.objects.filter(leave=leave, status="assigned")
        self.assertTrue(covers.exists())
        for cover in covers:
            self.assertNotEqual(cover.substitute_id, leave.faculty_id)
            clash = TimetableEntry.objects.filter(faculty=cover.substitute, weekday=day.weekday(), period=cover.period)
            self.assertFalse(clash.exists())
        self.assertTrue(Notification.objects.filter(user=covers.first().substitute.user, kind="substitution").exists())

    def test_faculty_leave_request_notifies_only_own_college_managers(self):
        faculty_user = User.objects.get(username="faculty1")
        faculty_user.college = self.demo_college
        faculty_user.save(update_fields=["college"])
        manager = User.objects.create_user(
            "second-manager", "manager2@x.io", "Demo-pass-123",
            role="college_admin", college=self.demo_college,
        )
        other_college = College.objects.create(name="Other College", code="OTHER", slug="other-college")
        other_manager = User.objects.create_user(
            "other-manager", "manager-other@x.io", "Demo-pass-123",
            role="college_admin", college=other_college,
        )
        client = APIClient()
        client.force_authenticate(faculty_user)
        today = date.today()
        response = client.post("/api/leaves/", {
            "start_date": today.isoformat(), "end_date": today.isoformat(), "reason": "Personal leave",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(Notification.objects.filter(user=self.admin, title="Leave request").exists())
        self.assertTrue(Notification.objects.filter(user=manager, title="Leave request").exists())
        self.assertFalse(Notification.objects.filter(user=other_manager, title="Leave request").exists())

    def test_auto_exam_invigilators_are_restricted_to_current_college(self):
        other_college = College.objects.create(
            name="Other College", code="OTHER", slug="other-college"
        )
        other_department = Department.objects.create(
            college=other_college, name="Other Computing", code="OC"
        )
        other_user = User.objects.create_user(
            "other-faculty", "other-faculty@example.test", "Demo-pass-123",
            role="faculty", college=other_college,
        )
        other_faculty = Faculty.objects.create(
            user=other_user, employee_id="OTHER-001", department=other_department
        )
        captured = {}

        def capture_invigilators(exams, faculty_pool, *args, **kwargs):
            captured["faculty_ids"] = {row["id"] for row in faculty_pool}
            return {}

        with patch(
            "apps.operations.services.engine.schedule_exams",
            return_value=SimpleNamespace(assignments=[], unscheduled=[]),
        ), patch(
            "apps.operations.services.engine.assign_invigilators",
            side_effect=capture_invigilators,
        ):
            services.auto_schedule_exams(
                self.semester, date(2026, 12, 1), date(2026, 12, 18),
                [], False, True, True, self.admin,
            )

        self.assertNotIn(other_faculty.id, captured["faculty_ids"])
        self.assertTrue(captured["faculty_ids"])

    def test_faculty_cannot_approve_leave(self):
        faculty_user = User.objects.get(username="faculty1")
        client = APIClient()
        client.force_authenticate(faculty_user)
        leave = FacultyLeave.objects.create(faculty=faculty_user.faculty_record, start_date=date.today(), end_date=date.today())
        self.assertEqual(client.post(f"/api/leaves/{leave.id}/approve/").status_code, 403)

    def test_students_are_blocked_from_operations(self):
        client = APIClient()
        client.force_authenticate(User.objects.get(username="student1"))
        self.assertEqual(client.get("/api/analytics/overview/").status_code, 403)

    def test_move_detects_conflicts_and_dry_run_does_not_apply(self):
        entry = TimetableEntry.objects.first()
        other = TimetableEntry.objects.exclude(pk=entry.pk).filter(faculty=entry.faculty).first()
        response = self.client.post(f"/api/timetable/entries/{entry.id}/move/", {
            "weekday": other.weekday, "period": other.period, "room": entry.room_id, "dry_run": True}, format="json")
        self.assertFalse(response.data["ok"])
        self.assertTrue(response.data["conflicts"])
        entry.refresh_from_db()
        self.assertNotEqual((entry.weekday, entry.period), (other.weekday, other.period))

    def test_auto_exam_preview_then_publish(self):
        payload = {"semester": self.semester.id, "start_date": "2026-12-01", "end_date": "2026-12-18", "preview": True}
        preview = self.client.post("/api/exams/auto-schedule/", payload, format="json")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.data["stats"]["unscheduled"], 0)
        self.assertEqual(self.client.get("/api/exam-schedules/").data["count"], 0)
        payload["preview"] = False
        self.assertEqual(self.client.post("/api/exams/auto-schedule/", payload, format="json").status_code, 200)
        self.assertEqual(self.client.get("/api/exam-schedules/").data["count"], preview.data["stats"]["exams"])

    def test_analytics_and_export(self):
        data = self.client.get("/api/analytics/overview/").data
        self.assertEqual(data["summary"]["conflicts"], 0)
        self.assertIn("insights", data)
        section = TimetableEntry.objects.first().section_id
        export = self.client.get(f"/api/exports/timetable/?scope=section&id={section}")
        self.assertEqual(export.status_code, 200)
        self.assertIn("spreadsheetml", export["Content-Type"])
