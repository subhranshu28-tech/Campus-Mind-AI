from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import College, User
from apps.campus.models import (
    AcademicYear,
    Course,
    Department,
    Semester,
    TimetableEntry,
    TimetableJob,
)


@override_settings(TIMETABLE_ASYNC_EAGER=True)
class AsyncTimetableJobTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", password="Demo-pass-123", verbosity=0)
        cls.college = College.objects.get(code="DEMO")
        cls.admin = User.objects.create_user(
            "job-admin",
            "job-admin@example.test",
            "Demo-pass-123",
            role="college_admin",
            college=cls.college,
        )
        cls.semester = Semester.objects.filter(sections__isnull=False).first() or Semester.objects.first()

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def _empty_semester(self):
        department = Department.objects.create(college=self.college, name="Empty Dept", code="EMPTY")
        course = Course.objects.create(department=department, name="Empty Course", code="EMPTY101")
        year = AcademicYear.objects.first()
        return Semester.objects.create(course=course, academic_year=year, number=1)

    def test_async_generation_succeeds_and_populates_timetable(self):
        # Remove the seeded timetable so the job has to produce new entries.
        TimetableEntry.objects.filter(section__semester=self.semester).delete()

        response = self.client.post(
            "/api/timetable/generate/async/",
            {"semester": self.semester.id},
            format="json",
        )

        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(response.data["status"], "succeeded")
        job = TimetableJob.objects.get(pk=response.data["id"])
        self.assertEqual(job.status, "succeeded")
        self.assertGreater(job.entry_count, 0)
        self.assertEqual(job.error, "")
        self.assertIsNotNone(job.started_at)
        self.assertIsNotNone(job.finished_at)
        self.assertTrue(TimetableEntry.objects.filter(section__semester=self.semester).exists())

    def test_async_generation_records_failure_reason(self):
        empty_semester = self._empty_semester()

        response = self.client.post(
            "/api/timetable/generate/async/",
            {"semester": empty_semester.id},
            format="json",
        )

        self.assertEqual(response.status_code, 202, response.data)
        job = TimetableJob.objects.get(pk=response.data["id"])
        self.assertEqual(job.status, "failed")
        self.assertIn("No teaching assignments", job.error)
        self.assertFalse(TimetableEntry.objects.filter(section__semester=empty_semester).exists())

    def test_job_status_endpoint_is_tenant_scoped(self):
        job = TimetableJob.objects.create(college=self.college, semester=self.semester)

        own_response = self.client.get(f"/api/timetable/jobs/{job.id}/")
        self.assertEqual(own_response.status_code, 200, own_response.data)
        self.assertEqual(own_response.data["id"], job.id)

        other_college = College.objects.create(name="Other College", code="OTHER", slug="other-college")
        other_admin = User.objects.create_user(
            "other-job-admin",
            "other-job-admin@example.test",
            "Demo-pass-123",
            role="college_admin",
            college=other_college,
        )
        other_client = APIClient()
        other_client.force_authenticate(other_admin)
        other_response = other_client.get(f"/api/timetable/jobs/{job.id}/")
        self.assertEqual(other_response.status_code, 404)

    def test_job_endpoints_require_authentication(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.get("/api/timetable/jobs/1/").status_code, 401)
        self.assertEqual(
            anonymous.post("/api/timetable/generate/async/", {"semester": self.semester.id}, format="json").status_code,
            401,
        )

    def test_cross_college_semester_is_rejected(self):
        other_college = College.objects.create(name="Other College", code="OTHER2", slug="other-college-2")
        other_department = Department.objects.create(college=other_college, name="Other Dept", code="OTH")
        other_course = Course.objects.create(department=other_department, name="Other Course", code="OTH101")
        other_semester = Semester.objects.create(
            course=other_course,
            academic_year=AcademicYear.objects.first(),
            number=1,
        )

        response = self.client.post(
            "/api/timetable/generate/async/",
            {"semester": other_semester.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("semester", response.data)


@override_settings(TIMETABLE_ASYNC_EAGER=False)
class DispatchedTimetableJobTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", password="Demo-pass-123", verbosity=0)
        cls.college = College.objects.get(code="DEMO")
        cls.admin = User.objects.create_user(
            "dispatch-admin",
            "dispatch-admin@example.test",
            "Demo-pass-123",
            role="college_admin",
            college=cls.college,
        )
        cls.semester = Semester.objects.first()

    @override_settings(
        TIMETABLE_ASYNC_EAGER=False,
        CELERY_TASK_ALWAYS_EAGER=False,
        CELERY_BROKER_URL="memory://",
    )
    def test_non_eager_request_queues_and_starts_worker(self):
        client = APIClient()
        client.force_authenticate(self.admin)

        with patch("apps.campus.jobs.run_timetable_job_task") as task:
            with self.captureOnCommitCallbacks(execute=True):
                response = client.post(
                    "/api/timetable/generate/async/",
                    {"semester": self.semester.id},
                    format="json",
                )

        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(response.data["status"], "queued")
        job = TimetableJob.objects.get(pk=response.data["id"])
        self.assertEqual(job.status, "queued")
        task.delay.assert_called_once()

    def test_worker_records_failure_for_missing_assignments(self):
        from apps.campus.jobs import run_timetable_job

        department = Department.objects.create(college=self.college, name="No Assign", code="NOASSIGN")
        course = Course.objects.create(department=department, name="No Assign Course", code="NA101")
        semester = Semester.objects.create(
            course=course,
            academic_year=AcademicYear.objects.first(),
            number=1,
        )
        job = TimetableJob.objects.create(college=self.college, semester=semester)

        run_timetable_job(job.id)

        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertIn("No teaching assignments", job.error)
