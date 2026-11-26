"""Shared fixtures for the ERP module API tests."""

from types import SimpleNamespace

from django.test import TestCase
from rest_framework.test import APIClient

from apps.campus.models import (
    AcademicYear,
    Course,
    Department,
    Faculty,
    Section,
    Semester,
    Student,
    Subject,
)

from .models import College, User


class ERPAPITestCase(TestCase):
    """Two isolated colleges, each with a complete campus graph."""

    def setUp(self):
        self.college = College.objects.create(
            name="Alpha Institute", code="ALPHA", slug="alpha"
        )
        self.other_college = College.objects.create(
            name="Beta Institute", code="BETA", slug="beta"
        )
        self.admin = self._user("erp-admin-a", "college_admin", self.college)
        self.student_user = self._user("erp-student-a", "student", self.college)
        self.other_admin = self._user(
            "erp-admin-b", "college_admin", self.other_college
        )
        self.other_student_user = self._user(
            "erp-student-b", "student", self.other_college
        )
        self.campus = self._build_campus(self.college, "A", self.student_user)
        self.other = self._build_campus(
            self.other_college, "B", self.other_student_user
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def _user(self, username, role, college):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.test",
            password="SafePass123!",
            role=role,
            college=college,
        )

    def _build_campus(self, college, suffix, student_user):
        key = suffix.lower()
        department = Department.objects.create(
            college=college, name=f"Computing {suffix}", code=f"CSE{suffix}"
        )
        academic_year = AcademicYear.objects.create(
            college=college,
            name=f"2026-{suffix}",
            starts_on="2026-06-01",
            ends_on="2027-05-31",
        )
        course = Course.objects.create(
            department=department,
            name=f"Computer Science {suffix}",
            code=f"BSC{suffix}",
            duration_years=4,
        )
        semester = Semester.objects.create(
            course=course, academic_year=academic_year, number=1
        )
        section = Section.objects.create(
            semester=semester, name=f"S{suffix}", capacity=60
        )
        subject = Subject.objects.create(
            course=course, semester=semester, code=f"CS{suffix}101", name="Programming"
        )
        faculty_user = self._user(f"erp-faculty-{key}", "faculty", college)
        faculty = Faculty.objects.create(
            user=faculty_user, employee_id=f"EMP-{suffix}", department=department
        )
        student = Student.objects.create(
            user=student_user,
            student_id=f"STU-{suffix}",
            department=department,
            semester=1,
            section=section,
            enrolled_on="2026-06-01",
        )
        return SimpleNamespace(
            department=department,
            academic_year=academic_year,
            course=course,
            semester=semester,
            section=section,
            subject=subject,
            faculty_user=faculty_user,
            faculty=faculty,
            student=student,
        )

    def add_student(self, name, section=None):
        """Add a second student to the primary college."""

        user = self._user(f"extra-{name}", "student", self.college)
        student = Student.objects.create(
            user=user,
            student_id=f"EXTRA-{name.upper()}",
            department=self.campus.department,
            semester=1,
            section=section or self.campus.section,
            enrolled_on="2026-06-01",
        )
        return user, student

    def as_student(self):
        self.client.force_authenticate(self.student_user)

    def as_admin(self):
        self.client.force_authenticate(self.admin)
