from apps.accounts.testing import ERPAPITestCase
from apps.campus.models import Section

from .models import Assignment, Submission


class AssignmentApiTests(ERPAPITestCase):
    def payload(self, **overrides):
        data = {
            "title": "Unit 1 problem set",
            "description": "Solve exercises 1-10.",
            "subject": self.campus.subject.id,
            "section": self.campus.section.id,
            "faculty": self.campus.faculty.id,
            "due_at": "2026-12-01T10:00:00Z",
            "max_marks": 25,
        }
        data.update(overrides)
        return data

    def create_assignment(self, college, campus, created_by=None):
        return Assignment.objects.create(
            college=college,
            title=f"Homework {college.code}",
            subject=campus.subject,
            section=campus.section,
            faculty=campus.faculty,
            due_at="2026-12-01T10:00:00Z",
            created_by=created_by,
        )

    def test_admin_create_sets_college_and_author_from_session(self):
        response = self.client.post("/api/assignments/", self.payload(), format="json")

        self.assertEqual(response.status_code, 201, response.data)
        assignment = Assignment.objects.get(pk=response.data["id"])
        self.assertEqual(assignment.college, self.college)
        self.assertEqual(assignment.created_by, self.admin)
        self.assertEqual(assignment.max_marks, 25)

    def test_create_rejects_subject_from_another_college(self):
        response = self.client.post(
            "/api/assignments/",
            self.payload(subject=self.other.subject.id),
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Assignment.objects.exists())

    def test_create_rejects_section_from_another_college(self):
        response = self.client.post(
            "/api/assignments/",
            self.payload(section=self.other.section.id),
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Assignment.objects.exists())

    def test_list_only_returns_the_caller_college(self):
        mine = self.create_assignment(self.college, self.campus, self.admin)
        self.create_assignment(self.other_college, self.other, self.other_admin)

        response = self.client.get("/api/assignments/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [mine.id])

    def test_faculty_may_manage_assignments_in_their_college(self):
        self.client.force_authenticate(self.campus.faculty_user)

        response = self.client.post("/api/assignments/", self.payload(), format="json")

        self.assertEqual(response.status_code, 201, response.data)

    def test_student_cannot_create_assignments(self):
        self.as_student()

        response = self.client.post("/api/assignments/", self.payload(), format="json")

        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(Assignment.objects.exists())

    def test_student_only_sees_assignments_for_their_section(self):
        own_section = self.create_assignment(self.college, self.campus)
        other_section = Section.objects.create(
            semester=self.campus.semester, name="OTHER", capacity=30
        )
        Assignment.objects.create(
            college=self.college,
            title="Other section homework",
            subject=self.campus.subject,
            section=other_section,
            faculty=self.campus.faculty,
            due_at="2026-12-02T10:00:00Z",
        )
        self.as_student()

        response = self.client.get("/api/assignments/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["id"] for row in response.data["results"]], [own_section.id]
        )


class SubmissionApiTests(ERPAPITestCase):
    def create_assignment(self):
        return Assignment.objects.create(
            college=self.college,
            title="Laboratory record",
            subject=self.campus.subject,
            section=self.campus.section,
            faculty=self.campus.faculty,
            due_at="2026-12-01T10:00:00Z",
        )

    def create_submission(self, assignment, student):
        return Submission.objects.create(assignment=assignment, student=student)

    def test_admin_can_list_submissions_for_their_college_only(self):
        assignment = self.create_assignment()
        mine = self.create_submission(assignment, self.campus.student)
        other_assignment = Assignment.objects.create(
            college=self.other_college,
            title="Beta record",
            subject=self.other.subject,
            section=self.other.section,
            faculty=self.other.faculty,
            due_at="2026-12-01T10:00:00Z",
        )
        self.create_submission(other_assignment, self.other.student)

        response = self.client.get("/api/submissions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [mine.id])

    def test_create_rejects_assignment_from_another_college(self):
        other_assignment = Assignment.objects.create(
            college=self.other_college,
            title="Beta record",
            subject=self.other.subject,
            section=self.other.section,
            faculty=self.other.faculty,
            due_at="2026-12-01T10:00:00Z",
        )

        response = self.client.post(
            "/api/submissions/",
            {
                "assignment": other_assignment.id,
                "student": self.campus.student.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Submission.objects.exists())

    def test_student_only_sees_their_own_submissions(self):
        assignment = self.create_assignment()
        mine = self.create_submission(assignment, self.campus.student)
        _, other_student = self.add_student("other")
        self.create_submission(assignment, other_student)
        self.as_student()

        response = self.client.get("/api/submissions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [mine.id])


class StudentSubmissionApiTests(ERPAPITestCase):
    def setUp(self):
        super().setUp()
        self.assignment = Assignment.objects.create(
            college=self.college,
            title="Lab record",
            subject=self.campus.subject,
            section=self.campus.section,
            faculty=self.campus.faculty,
            due_at="2026-12-01T10:00:00Z",
        )

    def test_student_can_submit_for_their_own_assignment(self):
        self.as_student()

        response = self.client.post(
            "/api/submissions/",
            {"assignment": self.assignment.id},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        submission = Submission.objects.get(pk=response.data["id"])
        self.assertEqual(submission.student, self.campus.student)
        self.assertIsNone(submission.marks)

    def test_student_cannot_submit_for_another_section(self):
        other_section = Section.objects.create(
            semester=self.campus.semester, name="OTHER", capacity=30
        )
        other_assignment = Assignment.objects.create(
            college=self.college,
            title="Other section homework",
            subject=self.campus.subject,
            section=other_section,
            faculty=self.campus.faculty,
            due_at="2026-12-02T10:00:00Z",
        )
        self.as_student()

        response = self.client.post(
            "/api/submissions/",
            {"assignment": other_assignment.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Submission.objects.exists())

    def test_student_cannot_submit_twice(self):
        Submission.objects.create(assignment=self.assignment, student=self.campus.student)
        self.as_student()

        response = self.client.post(
            "/api/submissions/",
            {"assignment": self.assignment.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)

    def test_student_cannot_grade_their_own_submission(self):
        self.as_student()

        response = self.client.post(
            "/api/submissions/",
            {
                "assignment": self.assignment.id,
                "marks": 100,
                "feedback": "self grade",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        submission = Submission.objects.get(pk=response.data["id"])
        self.assertIsNone(submission.marks)
        self.assertEqual(submission.feedback, "")

    def test_student_cannot_update_or_delete_submissions(self):
        submission = Submission.objects.create(
            assignment=self.assignment, student=self.campus.student
        )
        self.as_student()

        self.assertEqual(
            self.client.patch(
                f"/api/submissions/{submission.id}/",
                {"feedback": "x"},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.delete(f"/api/submissions/{submission.id}/").status_code, 403
        )

    def test_staff_can_grade_a_submission(self):
        submission = Submission.objects.create(
            assignment=self.assignment, student=self.campus.student
        )

        response = self.client.patch(
            f"/api/submissions/{submission.id}/",
            {"marks": 85, "feedback": "Good work"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        submission.refresh_from_db()
        self.assertEqual(submission.marks, 85)
        self.assertEqual(submission.feedback, "Good work")
