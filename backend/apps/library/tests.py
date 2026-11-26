from apps.accounts.testing import ERPAPITestCase

from .models import Book, BookIssue


class BookApiTests(ERPAPITestCase):
    def test_create_sets_college_from_session(self):
        response = self.client.post(
            "/api/books/",
            {
                "title": "Introduction to Algorithms",
                "author": "Cormen",
                "isbn": "9780262046305",
                "total_copies": 5,
                "available_copies": 5,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Book.objects.get(pk=response.data["id"]).college, self.college)

    def test_list_only_returns_the_caller_college(self):
        mine = Book.objects.create(college=self.college, title="Algorithms")
        Book.objects.create(college=self.other_college, title="Databases")

        response = self.client.get("/api/books/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [mine.id])

    def test_student_cannot_create_books(self):
        self.as_student()

        response = self.client.post("/api/books/", {"title": "Free book"}, format="json")

        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(Book.objects.exists())


class BookIssueApiTests(ERPAPITestCase):
    def setUp(self):
        super().setUp()
        self.book = Book.objects.create(
            college=self.college, title="Algorithms", total_copies=2, available_copies=2
        )
        self.other_book = Book.objects.create(
            college=self.other_college, title="Databases", total_copies=1, available_copies=1
        )

    def issue(self, book, student):
        return BookIssue.objects.create(book=book, student=student, due_on="2026-12-15")

    def test_create_rejects_book_from_another_college(self):
        response = self.client.post(
            "/api/book-issues/",
            {
                "book": self.other_book.id,
                "student": self.campus.student.id,
                "due_on": "2026-12-15",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(BookIssue.objects.exists())

    def test_create_rejects_student_from_another_college(self):
        response = self.client.post(
            "/api/book-issues/",
            {
                "book": self.book.id,
                "student": self.other.student.id,
                "due_on": "2026-12-15",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(BookIssue.objects.exists())

    def test_staff_can_issue_a_book(self):
        response = self.client.post(
            "/api/book-issues/",
            {
                "book": self.book.id,
                "student": self.campus.student.id,
                "due_on": "2026-12-15",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)

    def test_list_is_scoped_to_the_college(self):
        mine = self.issue(self.book, self.campus.student)
        self.issue(self.other_book, self.other.student)

        response = self.client.get("/api/book-issues/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [mine.id])

    def test_student_only_sees_their_own_issues(self):
        mine = self.issue(self.book, self.campus.student)
        _, other_student = self.add_student("library")
        self.issue(self.book, other_student)
        self.as_student()

        response = self.client.get("/api/book-issues/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [mine.id])

    def test_student_cannot_issue_books(self):
        self.as_student()

        response = self.client.post(
            "/api/book-issues/",
            {
                "book": self.book.id,
                "student": self.campus.student.id,
                "due_on": "2026-12-15",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(BookIssue.objects.exists())
