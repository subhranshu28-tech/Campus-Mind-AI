from django.test import TestCase
from rest_framework.test import APIClient

from .models import College, User
from apps.campus.models import Department
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
