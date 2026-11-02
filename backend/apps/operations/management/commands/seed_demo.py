import secrets
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import College, User
from apps.campus.models import (
    AcademicYear, Classroom, Course, Department, Faculty, Section, Semester, Student, Subject, TeachingAssignment,
)
from apps.campus.timetable_optimizer import generate_timetable
from apps.campus.models import TimetableEntry


class Command(BaseCommand):
    help = "Create a small demo college (departments, faculty, rooms, timetable) so the platform can be demoed immediately."

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Password for demo accounts (random if omitted).")

    @transaction.atomic
    def handle(self, *args, **options):
        college, _ = College.objects.get_or_create(code="DEMO", defaults={"name": "CampusMind Demo College", "slug": "campusmind-demo"})
        if Department.objects.filter(college=college, code="CSE").exists():
            self.stdout.write(self.style.WARNING("Demo data already present - nothing to do."))
            return
        password = options["password"] or secrets.token_urlsafe(10)
        dept = Department.objects.create(college=college, name="Computer Science & Engineering", code="CSE")
        year, _ = AcademicYear.objects.get_or_create(
            college=college, name="2026-27", defaults={"starts_on": date(2026, 7, 1), "ends_on": date(2027, 6, 30), "is_active": True})
        course = Course.objects.create(department=dept, name="B.Tech CSE", code="BTCSE", duration_years=4)
        semester = Semester.objects.create(course=course, academic_year=year, number=3)
        sections = [Section.objects.create(semester=semester, name=name, capacity=50) for name in ("A", "B")]

        faculty = []
        for index, name in enumerate(["Asha Rao", "Vikram Sen", "Meera Das", "Rohan Iyer", "Nisha Gupta", "Arjun Nair"], 1):
            first, last = name.split()
            user = User.objects.create_user(username=f"faculty{index}", email=f"faculty{index}@demo.local",
                                            password=password, first_name=first, last_name=last, role="faculty", college=college)
            faculty.append(Faculty.objects.create(user=user, employee_id=f"EMP{index:03d}", department=dept, qualification="M.Tech"))

        for index, (code, name, lab) in enumerate([
            ("CS301", "Data Structures", False), ("CS302", "Operating Systems", False), ("CS303", "Database Systems", False),
            ("CS304", "Discrete Mathematics", False), ("CS311", "Data Structures Lab", True), ("CS312", "DBMS Lab", True),
        ]):
            subject = Subject.objects.create(course=course, semester=semester, code=code, name=name, is_lab=lab, credits=2 if lab else 4)
            for section_index, section in enumerate(sections):
                TeachingAssignment.objects.create(
                    section=section, subject=subject, faculty=faculty[(index + section_index) % len(faculty)],
                    periods_per_week=2 if lab else 3)

        for code, name, capacity, lab in [("R101", "Room 101", 60, False), ("R102", "Room 102", 60, False), ("R103", "Room 103", 60, False),
                                         ("R201", "Seminar Hall", 120, False), ("LAB1", "Computing Lab 1", 60, True), ("LAB2", "Computing Lab 2", 60, True)]:
            Classroom.objects.create(college=college, code=code, name=name, capacity=capacity, is_lab=lab)

        for number in range(1, 7):
            user = User.objects.create_user(username=f"student{number}", email=f"student{number}@demo.local",
                                            password=password, first_name="Student", last_name=str(number), role="student", college=college)
            Student.objects.create(user=user, student_id=f"S26{number:03d}", department=dept, semester=3,
                                   section=sections[number % 2], enrolled_on=date(2026, 7, 15))

        TimetableEntry.objects.bulk_create(generate_timetable(semester))
        self.stdout.write(self.style.SUCCESS("Demo college created: 6 faculty, 6 students, 6 rooms, generated timetable."))
        self.stdout.write(f"Demo logins: faculty1..faculty6 and student1..student6 / password: {password}")
