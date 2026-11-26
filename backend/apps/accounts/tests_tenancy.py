from django.test import TestCase
from rest_framework.test import APIClient

from .models import College, User
from apps.campus.models import (
    AcademicYear,
    Classroom,
    Course,
    Department,
    ExamSchedule,
    Faculty,
    Section,
    Semester,
    Subject,
)
from apps.operations.models import AuditLog
from .tenancy import scope_queryset


class CollegeTenantIsolationTests(TestCase):
    def setUp(self):
        self.college_a = College.objects.create(name="Alpha Institute", code="ALPHA", slug="alpha")
        self.college_b = College.objects.create(name="Beta Institute", code="BETA", slug="beta")
        self.user_a = User.objects.create_user(username="alpha-admin", email="a@example.test", password="SafePass123!", role="college_admin", college=self.college_a)
        self.user_b = User.objects.create_user(username="beta-admin", email="b@example.test", password="SafePass123!", role="college_admin", college=self.college_b)
        self.department_a = Department.objects.create(college=self.college_a, name="Computer Science", code="CSE")
        self.department_b = Department.objects.create(college=self.college_b, name="Computer Science", code="CSE")

    def test_queryset_scope_never_returns_another_colleges_rows(self):
        visible = scope_queryset(Department.objects.all(), self.user_a)
        self.assertEqual(list(visible), [self.department_a])
        self.assertNotIn(self.department_b, visible)

    def test_api_list_and_related_writes_are_tenant_scoped(self):
        client = APIClient()
        client.force_authenticate(self.user_a)
        response = client.get("/api/departments/")
        self.assertEqual(response.status_code, 200)
        rows = response.data.get("results", response.data)
        self.assertEqual([row["id"] for row in rows], [self.department_a.id])
        rejected = client.post("/api/courses/", {
            "department": self.department_b.id, "name": "Computer Science", "code": "CSE-BTECH", "duration_years": 4,
        }, format="json")
        self.assertEqual(rejected.status_code, 400)
        self.assertFalse(self.department_b.courses.exists())

    def test_college_registration_creates_tenant_admin(self):
        client = APIClient()
        response = client.post("/api/auth/register-college/", {
            "college_name": "Gamma Polytechnic", "college_code": "GAMMA",
            "admin_name": "Gamma Admin", "username": "gamma-admin",
            "email": "gamma@example.test", "password": "StrongPassword!234",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(username="gamma-admin")
        self.assertEqual(user.role, "college_admin")
        self.assertEqual(user.college.code, "GAMMA")

    def _scheduling_setup(self, college, suffix):
        department = Department.objects.create(college=college, name=f"Computing {suffix}", code=f"CSE{suffix}")
        academic_year = AcademicYear.objects.create(
            college=college, name=f"2026-{suffix}", starts_on="2026-09-01", ends_on="2027-06-30",
        )
        course = Course.objects.create(department=department, name="CS", code=f"BSC{suffix}", duration_years=4)
        semester = Semester.objects.create(course=course, academic_year=academic_year, number=1)
        section = Section.objects.create(semester=semester, name="A", capacity=30)
        subject = Subject.objects.create(course=course, semester=semester, code=f"CS{suffix}01", name="Programming")
        faculty_user = User.objects.create_user(
            username=f"faculty-{suffix}", email=f"faculty-{suffix}@example.test",
            password="SafePass123!", role="faculty", college=college,
        )
        faculty = Faculty.objects.create(user=faculty_user, employee_id=f"FAC-{suffix}", department=department)
        room = Classroom.objects.create(college=college, name="Room 101", code=f"R{suffix}101", capacity=40)
        return section, subject, room, faculty

    def test_exam_conflicts_are_scoped_to_the_users_college(self):
        section_b, subject_b, room_b, _ = self._scheduling_setup(self.college_b, "B")
        ExamSchedule.objects.create(
            section=section_b, subject=subject_b, room=room_b,
            date="2026-12-01", start_period=1, duration_periods=2,
        )
        section_a, subject_a, room_a, _ = self._scheduling_setup(self.college_a, "A")
        client = APIClient()
        client.force_authenticate(self.user_a)
        response = client.post("/api/exam-schedules/", {
            "section": section_a.id, "subject": subject_a.id, "room": room_a.id,
            "date": "2026-12-01", "start_period": 1, "duration_periods": 2,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(ExamSchedule.objects.filter(section__semester__course__department__college=self.college_a).count(), 1)

    def test_exam_write_rejects_another_colleges_room(self):
        section_a, subject_a, _, _ = self._scheduling_setup(self.college_a, "A")
        _, _, room_b, _ = self._scheduling_setup(self.college_b, "B")
        client = APIClient()
        client.force_authenticate(self.user_a)
        response = client.post("/api/exam-schedules/", {
            "section": section_a.id, "subject": subject_a.id, "room": room_b.id,
            "date": "2026-12-01", "start_period": 1, "duration_periods": 2,
        }, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("room", response.data)

    def test_audit_logs_are_scoped_by_college_even_without_an_actor(self):
        AuditLog.objects.create(college=self.college_b, action="system.job", entity="System")
        AuditLog.objects.create(college=self.college_a, actor=None, action="system.job", entity="System")
        visible = scope_queryset(AuditLog.objects.all(), self.user_a)
        self.assertEqual(visible.count(), 1)
        self.assertEqual(visible.first().college_id, self.college_a.id)

    def test_audit_log_chain_is_tamper_evident(self):
        first = AuditLog.objects.create(college=self.college_a, actor=self.user_a, action="demo.first", entity="Demo")
        second = AuditLog.objects.create(college=self.college_a, actor=self.user_a, action="demo.second", entity="Demo")
        self.assertTrue(AuditLog.verify_chain(self.college_a))
        self.assertEqual(second.previous_hash, first.entry_hash)
        # Tampering with a row breaks the chain.
        AuditLog.objects.filter(pk=first.pk).update(action="demo.tampered")
        first.refresh_from_db()
        self.assertFalse(AuditLog.verify_chain(self.college_a))
