from apps.accounts.testing import ERPAPITestCase

from .models import Company, JobPosting, PlacementApplication


class CompanyApiTests(ERPAPITestCase):
    def test_create_sets_college_from_session(self):
        response = self.client.post(
            "/api/companies/",
            {
                "name": "Acme Software",
                "industry": "Software",
                "contact_email": "hr@acme.test",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(
            Company.objects.get(pk=response.data["id"]).college, self.college
        )

    def test_list_only_returns_the_caller_college(self):
        mine = Company.objects.create(college=self.college, name="Acme")
        Company.objects.create(college=self.other_college, name="Globex")

        response = self.client.get("/api/companies/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [mine.id])

    def test_student_cannot_create_companies(self):
        self.as_student()

        response = self.client.post(
            "/api/companies/", {"name": "Free job"}, format="json"
        )

        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(Company.objects.exists())

    def test_job_posting_rejects_company_from_another_college(self):
        other_company = Company.objects.create(
            college=self.other_college, name="Globex"
        )

        response = self.client.post(
            "/api/job-postings/",
            {"company": other_company.id, "title": "Intern"},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(JobPosting.objects.exists())


class PlacementApplicationApiTests(ERPAPITestCase):
    def setUp(self):
        super().setUp()
        self.company = Company.objects.create(college=self.college, name="Acme")
        self.job = JobPosting.objects.create(company=self.company, title="Engineer")
        other_company = Company.objects.create(
            college=self.other_college, name="Globex"
        )
        self.other_job = JobPosting.objects.create(
            company=other_company, title="Analyst"
        )

    def apply(self, job, student):
        return PlacementApplication.objects.create(job=job, student=student)

    def test_create_rejects_job_from_another_college(self):
        response = self.client.post(
            "/api/placement-applications/",
            {"job": self.other_job.id, "student": self.campus.student.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(PlacementApplication.objects.exists())

    def test_create_rejects_student_from_another_college(self):
        response = self.client.post(
            "/api/placement-applications/",
            {"job": self.job.id, "student": self.other.student.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(PlacementApplication.objects.exists())

    def test_staff_can_record_an_application(self):
        response = self.client.post(
            "/api/placement-applications/",
            {"job": self.job.id, "student": self.campus.student.id},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)

    def test_student_only_sees_their_own_applications(self):
        mine = self.apply(self.job, self.campus.student)
        _, other_student = self.add_student("placement")
        self.apply(self.job, other_student)
        self.as_student()

        response = self.client.get("/api/placement-applications/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [mine.id])
