"""College-scoped uniqueness should return 400, never a 500 IntegrityError."""

from rest_framework import status

from apps.accounts.testing import ERPAPITestCase


class CollegeScopedUniqueTests(ERPAPITestCase):
    def test_duplicate_department_name_is_rejected(self):
        response = self.client.post(
            "/api/departments/",
            {"name": self.campus.department.name, "code": "NEW1"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_duplicate_department_code_is_rejected(self):
        response = self.client.post(
            "/api/departments/",
            {"name": "Another Department", "code": self.campus.department.code},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", response.data)

    def test_duplicate_academic_year_is_rejected(self):
        response = self.client.post(
            "/api/academic-years/",
            {
                "name": self.campus.academic_year.name,
                "starts_on": "2027-06-01",
                "ends_on": "2028-05-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_duplicate_classroom_code_is_rejected(self):
        self.client.post(
            "/api/classrooms/",
            {"name": "Room 1", "code": "R1", "capacity": 30},
            format="json",
        )
        response = self.client.post(
            "/api/classrooms/",
            {"name": "Room 2", "code": "R1", "capacity": 40},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", response.data)

    def test_same_names_are_allowed_across_colleges(self):
        self.client.force_authenticate(self.other_admin)
        response = self.client.post(
            "/api/departments/",
            {"name": self.campus.department.name, "code": "DUP"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
