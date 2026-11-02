import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import College
from apps.campus.models import (
    AcademicYear,
    AttendanceRecord,
    Classroom,
    Course,
    Department,
    ExamSchedule,
    Faculty,
    FacultyAvailability,
    Section,
    Semester,
    Student,
    Subject,
    TeachingAssignment,
    TimetableEntry,
)

User = get_user_model()


class CampusApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.college = College.objects.create(name="Test College", code="TEST", slug="test-college")
        self.admin = User.objects.create_user(
            college=self.college, username="admin", email="admin@example.edu", password="StrongPass123!",
            role=User.Role.COLLEGE_ADMIN,
        )

    def test_jwt_login_and_current_user(self):
        response = self.client.post(
            "/api/auth/token/",
            {"username": "admin", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        current_user = self.client.get("/api/auth/me/")
        self.assertEqual(current_user.status_code, 200)
        self.assertEqual(current_user.data["role"], User.Role.COLLEGE_ADMIN)

    def test_dashboard_requires_authentication(self):
        self.assertEqual(self.client.get("/api/dashboard/summary/").status_code, 401)

    def test_department_create_is_role_restricted(self):
        student = User.objects.create_user(
            college=self.college, username="student", email="student@example.edu", password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        self.client.force_authenticate(student)
        response = self.client.post(
            "/api/departments/", {"name": "Computing", "code": "CSE"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Department.objects.count(), 0)

    def test_department_create_for_college_admin(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/departments/", {"name": "Computing", "code": "CSE"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Department.objects.get().code, "CSE")

    def test_dashboard_uses_database_counts(self):
        self.client.force_authenticate(self.admin)
        Department.objects.create(college=self.college, name="Computing", code="CSE")
        response = self.client.get("/api/dashboard/summary/")
        self.assertEqual(response.data["departments"], 1)
        self.assertEqual(response.data["students"], 0)

    def test_student_creation_creates_a_hashed_student_account(self):
        department = Department.objects.create(college=self.college, name="Computing", code="CSE")
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/students/",
            {
                "user": {
                    "username": "student01",
                    "email": "student01@example.edu",
                    "first_name": "Ari",
                    "last_name": "Student",
                    "password": "StrongPass123!",
                },
                "student_id": "STU-001",
                "department": department.id,
                "semester": 1,
                "enrolled_on": "2026-09-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        student = Student.objects.get(student_id="STU-001")
        self.assertEqual(student.user.role, User.Role.STUDENT)
        self.assertTrue(student.user.check_password("StrongPass123!"))
        self.assertNotIn("password", response.data["user"])

    def test_student_creation_accepts_string_primary_keys_for_matching_section(self):
        department = Department.objects.create(college=self.college, name="Computing", code="CSE")
        year = AcademicYear.objects.create(
            college=self.college, name="2026-27", starts_on="2026-06-01", ends_on="2027-05-31"
        )
        course = Course.objects.create(department=department, name="Computer Science", code="CSE")
        semester = Semester.objects.create(course=course, academic_year=year, number=1)
        section = Section.objects.create(semester=semester, name="A", capacity=60)
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/students/",
            {
                "user": {
                    "username": "sectionstudent", "email": "sectionstudent@example.edu",
                    "first_name": "Section", "last_name": "Student", "password": "StrongPass123!",
                },
                "student_id": "STU-SECTION-001", "department": str(department.id),
                "semester": "1", "section": str(section.id), "enrolled_on": "2026-09-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Student.objects.get(student_id="STU-SECTION-001").section_id, section.id)

    def test_attendance_is_recorded_and_duplicate_date_is_rejected(self):
        department = Department.objects.create(college=self.college, name="Computing", code="CSE")
        student_user = User.objects.create_user(
            college=self.college, username="student01", email="student01@example.edu", password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        student = Student.objects.create(
            user=student_user, student_id="STU-001", department=department,
            semester=1, enrolled_on="2026-09-01",
        )
        self.client.force_authenticate(self.admin)
        payload = {"student": student.id, "date": "2026-10-01", "is_present": True}
        created = self.client.post("/api/attendance/", payload, format="json")
        duplicate = self.client.post("/api/attendance/", payload, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(AttendanceRecord.objects.count(), 1)
        self.assertEqual(AttendanceRecord.objects.get().recorded_by, self.admin)

    def test_academic_year_rejects_end_date_before_start(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/academic-years/",
            {"name": "2026", "starts_on": "2026-09-01", "ends_on": "2026-08-31"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AcademicYear.objects.count(), 0)

    def test_only_one_academic_year_can_be_active(self):
        AcademicYear.objects.create(
            college=self.college, name="2025-2026", starts_on="2025-09-01", ends_on="2026-06-30", is_active=True,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/academic-years/",
            {"name": "2026-2027", "starts_on": "2026-09-01", "ends_on": "2027-06-30", "is_active": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AcademicYear.objects.filter(is_active=True).count(), 1)

    def test_academic_course_semester_section_and_subject_workflow(self):
        department = Department.objects.create(college=self.college, name="Computing", code="CSE")
        academic_year = AcademicYear.objects.create(
            college=self.college, name="2026-2027", starts_on="2026-09-01", ends_on="2027-06-30", is_active=True,
        )
        self.client.force_authenticate(self.admin)
        course_response = self.client.post(
            "/api/courses/",
            {"department": department.id, "name": "Computer Science", "code": "BSC-CS", "duration_years": 4},
            format="json",
        )
        self.assertEqual(course_response.status_code, 201, course_response.data)
        course_id = course_response.data["id"]
        semester_response = self.client.post(
            "/api/semesters/",
            {"course": course_id, "academic_year": academic_year.id, "number": 1},
            format="json",
        )
        self.assertEqual(semester_response.status_code, 201, semester_response.data)
        semester_id = semester_response.data["id"]
        section_response = self.client.post(
            "/api/sections/", {"semester": semester_id, "name": "A", "capacity": 60}, format="json"
        )
        self.assertEqual(section_response.status_code, 201, section_response.data)
        subject_response = self.client.post(
            "/api/subjects/",
            {"course": course_id, "semester": semester_id, "code": "CS101", "name": "Programming", "credits": 4},
            format="json",
        )
        self.assertEqual(subject_response.status_code, 201, subject_response.data)

    def test_faculty_creation_creates_a_hashed_faculty_account(self):
        department = Department.objects.create(college=self.college, name="Computing", code="CSE")
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/faculty/",
            {
                "user": {
                    "username": "faculty01",
                    "email": "faculty01@example.edu",
                    "first_name": "Ari",
                    "last_name": "Faculty",
                    "password": "StrongPass123!",
                },
                "employee_id": "FAC-001",
                "department": department.id,
                "qualification": "MSc",
                "experience_years": 3,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        faculty = Faculty.objects.get(employee_id="FAC-001")
        self.assertEqual(faculty.user.role, User.Role.FACULTY)
        self.assertTrue(faculty.user.check_password("StrongPass123!"))

    def test_student_cannot_read_or_manage_campus_records(self):
        student = User.objects.create_user(
            college=self.college, username="student", email="student@example.edu", password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        self.client.force_authenticate(student)
        self.assertEqual(self.client.get("/api/students/").status_code, 403)
        self.assertEqual(
            self.client.post(
                "/api/departments/", {"name": "Computing", "code": "CSE"}, format="json"
            ).status_code,
            403,
        )

    def test_student_portal_only_returns_the_signed_in_students_records(self):
        department = Department.objects.create(college=self.college, name="Computing", code="CSE")
        student_user = User.objects.create_user(
            college=self.college, username="student01", email="student01@example.edu", password="StrongPass123!",
            first_name="Ari", last_name="Student", role=User.Role.STUDENT,
        )
        other_user = User.objects.create_user(
            college=self.college, username="student02", email="student02@example.edu", password="StrongPass123!",
            first_name="Other", last_name="Student", role=User.Role.STUDENT,
        )
        student = Student.objects.create(
            user=student_user, student_id="STU-001", department=department,
            semester=1, enrolled_on="2026-09-01",
        )
        other_student = Student.objects.create(
            user=other_user, student_id="STU-002", department=department,
            semester=1, enrolled_on="2026-09-01",
        )
        AttendanceRecord.objects.create(
            student=student, date="2026-10-01", is_present=True, recorded_by=self.admin,
        )
        AttendanceRecord.objects.create(
            student=other_student, date="2026-10-01", is_present=False, recorded_by=self.admin,
        )
        self.client.force_authenticate(student_user)
        self.assertEqual(self.client.get("/api/dashboard/summary/").status_code, 403)
        response = self.client.get("/api/student/portal/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["attendance"]["percentage"], 100)
        self.assertEqual(len(response.data["attendance"]["records"]), 1)
        self.assertEqual(response.data["attendance"]["records"][0]["student_id"], "STU-001")
        self.assertNotIn("students", response.data)
        self.assertNotIn("faculty", response.data)
        self.assertNotIn("departments", response.data)

    def test_teacher_subject_pdfs_are_only_visible_to_assigned_students(self):
        _, _, section, subject, faculty, _, _ = self.create_scheduling_setup()
        other_section = Section.objects.create(semester=section.semester, name="B", capacity=30)
        student_user = User.objects.create_user(
            college=self.college, username="student01", email="student01@example.edu", password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        Student.objects.create(
            user=student_user, student_id="STU-001", department=faculty.department,
            semester=1, section=section, enrolled_on="2026-09-01",
        )
        other_student_user = User.objects.create_user(
            college=self.college, username="student02", email="student02@example.edu", password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        Student.objects.create(
            user=other_student_user, student_id="STU-002", department=faculty.department,
            semester=1, section=other_section, enrolled_on="2026-09-01",
        )
        media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(media_directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

        self.client.force_authenticate(faculty.user)
        teaching_subjects = self.client.get("/api/subject-notes/subjects/")
        self.assertEqual(teaching_subjects.status_code, 200, teaching_subjects.data)
        self.assertEqual(
            teaching_subjects.data,
            [{"id": subject.id, "code": subject.code, "name": subject.name}],
        )
        created = self.client.post(
            "/api/subject-notes/",
            {
                "subject": subject.id,
                "title": "Unit One",
                "description": "Lecture notes",
                "file": SimpleUploadedFile(
                    "unit-one.pdf", b"%PDF-1.4\nUnit one notes", content_type="application/pdf"
                ),
            },
            format="multipart",
        )
        self.assertEqual(created.status_code, 201, created.data)
        note_id = created.data["id"]

        self.client.force_authenticate(student_user)
        note_list = self.client.get("/api/subject-notes/")
        self.assertEqual(note_list.status_code, 200)
        self.assertEqual([item["id"] for item in note_list.data["results"]], [note_id])
        download = self.client.get(f"/api/subject-notes/{note_id}/download/")
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download["Content-Type"], "application/pdf")
        download.close()

        self.client.force_authenticate(other_student_user)
        self.assertEqual(self.client.get("/api/subject-notes/").data["results"], [])
        self.assertEqual(
            self.client.get(f"/api/subject-notes/{note_id}/download/").status_code, 404
        )

    def test_faculty_cannot_upload_unassigned_subject_or_non_pdf(self):
        department, _, _, subject, faculty, _, _ = self.create_scheduling_setup()
        other_course = Course.objects.create(
            department=department, name="Mathematics", code="BSC-MATH", duration_years=4,
        )
        other_year = AcademicYear.objects.create(
            college=self.college, name="2027-2028", starts_on="2027-09-01", ends_on="2028-06-30",
        )
        other_semester = Semester.objects.create(
            course=other_course, academic_year=other_year, number=1,
        )
        other_subject = Subject.objects.create(
            course=other_course, semester=other_semester, code="MATH101", name="Mathematics",
        )
        media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(media_directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.client.force_authenticate(faculty.user)

        unassigned = self.client.post(
            "/api/subject-notes/",
            {
                "subject": other_subject.id,
                "title": "Not assigned",
                "file": SimpleUploadedFile("notes.pdf", b"%PDF-1.4\nvalid", content_type="application/pdf"),
            },
            format="multipart",
        )
        self.assertEqual(unassigned.status_code, 400)
        invalid = self.client.post(
            "/api/subject-notes/",
            {
                "subject": subject.id,
                "title": "Invalid file",
                "file": SimpleUploadedFile("notes.pdf", b"not a pdf", content_type="application/pdf"),
            },
            format="multipart",
        )
        self.assertEqual(invalid.status_code, 400)

    def test_previous_question_papers_are_uploaded_and_scoped_to_students(self):
        _, _, section, subject, faculty, _, _ = self.create_scheduling_setup()
        other_section = Section.objects.create(semester=section.semester, name="B", capacity=30)
        student_user = User.objects.create_user(
            college=self.college, username="student01", email="student01@example.edu", password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        Student.objects.create(
            user=student_user, student_id="STU-001", department=faculty.department,
            semester=1, section=section, enrolled_on="2026-09-01",
        )
        other_student_user = User.objects.create_user(
            college=self.college, username="student02", email="student02@example.edu", password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        Student.objects.create(
            user=other_student_user, student_id="STU-002", department=faculty.department,
            semester=1, section=other_section, enrolled_on="2026-09-01",
        )
        media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(media_directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

        self.client.force_authenticate(faculty.user)
        uploaded = self.client.post(
            "/api/question-papers/",
            {
                "subject": subject.id,
                "title": "Final examination",
                "exam_year": 2024,
                "description": "Previous final paper",
                "file": SimpleUploadedFile(
                    "final-2024.pdf", b"%PDF-1.4\nQuestion paper", content_type="application/pdf"
                ),
            },
            format="multipart",
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.data)
        paper_id = uploaded.data["id"]

        self.client.force_authenticate(student_user)
        papers = self.client.get("/api/question-papers/")
        self.assertEqual(papers.status_code, 200)
        self.assertEqual([paper["id"] for paper in papers.data["results"]], [paper_id])
        self.assertEqual(papers.data["results"][0]["exam_year"], 2024)

        self.client.force_authenticate(other_student_user)
        self.assertEqual(self.client.get("/api/question-papers/").data["results"], [])
        self.assertEqual(
            self.client.get(f"/api/question-papers/{paper_id}/download/").status_code, 404
        )

    def test_question_paper_upload_rejects_future_exam_year(self):
        _, _, _, subject, faculty, _, _ = self.create_scheduling_setup()
        media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(media_directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.client.force_authenticate(faculty.user)
        response = self.client.post(
            "/api/question-papers/",
            {
                "subject": subject.id,
                "title": "Future exam",
                "exam_year": 9999,
                "file": SimpleUploadedFile(
                    "future.pdf", b"%PDF-1.4\nQuestion paper", content_type="application/pdf"
                ),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("exam_year", response.data)

    def test_department_cannot_be_deleted_while_student_records_reference_it(self):
        department = Department.objects.create(college=self.college, name="Computing", code="CSE")
        student_user = User.objects.create_user(
            college=self.college, username="student01", email="student01@example.edu", password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        Student.objects.create(
            user=student_user, student_id="STU-001", department=department,
            semester=1, enrolled_on="2026-09-01",
        )
        self.client.force_authenticate(self.admin)
        response = self.client.delete(f"/api/departments/{department.id}/")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Department.objects.filter(pk=department.id).exists())

    def create_scheduling_setup(self, *, is_lab=False, room_is_lab=False):
        department = Department.objects.create(college=self.college, name="Computing", code="CSE")
        academic_year = AcademicYear.objects.create(
            college=self.college, name="2026-2027", starts_on="2026-09-01", ends_on="2027-06-30", is_active=True,
        )
        course = Course.objects.create(
            department=department, name="Computer Science", code="BSC-CS", duration_years=4,
        )
        semester = Semester.objects.create(course=course, academic_year=academic_year, number=1)
        section = Section.objects.create(semester=semester, name="A", capacity=30)
        subject = Subject.objects.create(
            course=course, semester=semester, code="CS101", name="Programming",
            is_lab=is_lab, credits=3,
        )
        faculty_user = User.objects.create_user(
            college=self.college, username="faculty01", email="faculty01@example.edu",
            password="StrongPass123!", role=User.Role.FACULTY,
        )
        faculty = Faculty.objects.create(
            user=faculty_user, employee_id="FAC-001", department=department,
        )
        room = Classroom.objects.create(
            college=self.college, name="Room 101", code="R101", capacity=40, is_lab=room_is_lab,
        )
        assignment = TeachingAssignment.objects.create(
            section=section, subject=subject, faculty=faculty, periods_per_week=1,
        )
        return department, semester, section, subject, faculty, room, assignment

    def test_ai_timetable_generates_conflict_free_sessions_using_availability(self):
        department, semester, first_section, subject, faculty, room, first_assignment = (
            self.create_scheduling_setup()
        )
        second_section = Section.objects.create(semester=semester, name="B", capacity=30)
        second_assignment = TeachingAssignment.objects.create(
            section=second_section, subject=subject, faculty=faculty, periods_per_week=1,
        )
        available_slots = {(0, 1), (1, 2)}
        FacultyAvailability.objects.bulk_create([
            FacultyAvailability(
                faculty=faculty, weekday=weekday, period=period,
                is_available=(weekday, period) in available_slots,
            )
            for weekday in range(5)
            for period in range(1, 9)
        ])
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/timetable/generate/", {"semester": semester.id}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        entries = list(TimetableEntry.objects.filter(section__semester=semester))
        self.assertEqual(len(entries), 2)
        self.assertEqual(response.data["entry_count"], 2)
        self.assertEqual(len({(entry.weekday, entry.period) for entry in entries}), 2)
        self.assertTrue(all((entry.weekday, entry.period) in available_slots for entry in entries))
        self.assertTrue(all(entry.room_id == room.id for entry in entries))
        self.assertEqual({entry.assignment_id for entry in entries}, {first_assignment.id, second_assignment.id})

    def test_ai_timetable_reports_missing_lab_instead_of_saving_conflicts(self):
        _, semester, _, _, _, _, _ = self.create_scheduling_setup(is_lab=True)
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/timetable/generate/", {"semester": semester.id}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("laboratory", str(response.data).lower())
        self.assertEqual(TimetableEntry.objects.count(), 0)

    def test_timetable_substitution_suggests_available_subject_expert(self):
        department, semester, section, subject, faculty, room, assignment = (
            self.create_scheduling_setup()
        )
        candidate_user = User.objects.create_user(
            college=self.college, username="faculty02", email="faculty02@example.edu",
            password="StrongPass123!", role=User.Role.FACULTY,
        )
        candidate = Faculty.objects.create(
            user=candidate_user, employee_id="FAC-002", department=department,
        )
        second_section = Section.objects.create(semester=semester, name="B", capacity=30)
        TeachingAssignment.objects.create(
            section=second_section, subject=subject, faculty=candidate, periods_per_week=1,
        )
        entry = TimetableEntry.objects.create(
            assignment=assignment, section=section, subject=subject, faculty=faculty,
            room=room, weekday=0, period=1,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.get(f"/api/timetable/entries/{entry.id}/substitutions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["faculty"] for item in response.data["suggestions"]], [candidate.id])

    def test_exam_schedule_prevents_room_time_overlap(self):
        _, _, section, subject, _, room, _ = self.create_scheduling_setup()
        self.client.force_authenticate(self.admin)
        payload = {
            "section": section.id, "subject": subject.id, "room": room.id,
            "date": "2026-12-01", "start_period": 2, "duration_periods": 2,
        }
        first = self.client.post("/api/exam-schedules/", payload, format="json")
        second = self.client.post(
            "/api/exam-schedules/",
            {**payload, "section": section.id, "start_period": 3},
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(ExamSchedule.objects.count(), 1)

    def test_exam_schedule_rejects_invigilator_unavailability(self):
        _, _, section, subject, faculty, room, _ = self.create_scheduling_setup()
        FacultyAvailability.objects.create(
            faculty=faculty, weekday=0, period=1, is_available=False,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/exam-schedules/",
            {
                "section": section.id, "subject": subject.id, "room": room.id,
                "invigilator": faculty.id, "date": "2026-12-07",
                "start_period": 1, "duration_periods": 1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("invigilator", response.data)

    def test_exam_schedule_rejects_recurring_classroom_conflict(self):
        _, _, section, subject, faculty, room, assignment = self.create_scheduling_setup()
        TimetableEntry.objects.create(
            assignment=assignment, section=section, subject=subject, faculty=faculty,
            room=room, weekday=0, period=1,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/exam-schedules/",
            {
                "section": section.id, "subject": subject.id, "room": room.id,
                "date": "2026-12-07", "start_period": 1, "duration_periods": 1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("start_period", response.data)
