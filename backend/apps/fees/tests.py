from apps.accounts.testing import ERPAPITestCase

from .models import FeeStructure, Invoice, Payment


class FeeStructureApiTests(ERPAPITestCase):
    def test_admin_create_sets_college_from_session(self):
        response = self.client.post(
            "/api/fee-structures/",
            {"name": "Tuition 2026", "amount": "45000.00", "description": "Annual"},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        structure = FeeStructure.objects.get(pk=response.data["id"])
        self.assertEqual(structure.college, self.college)

    def test_college_cannot_be_supplied_in_the_request(self):
        response = self.client.post(
            "/api/fee-structures/",
            {
                "name": "Tuition 2026",
                "amount": "45000.00",
                "college": self.other_college.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(
            FeeStructure.objects.get(pk=response.data["id"]).college, self.college
        )

    def test_duplicate_name_within_college_is_rejected(self):
        FeeStructure.objects.create(
            college=self.college, name="Tuition 2026", amount="45000.00"
        )

        response = self.client.post(
            "/api/fee-structures/",
            {"name": "Tuition 2026", "amount": "50000.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)

    def test_list_only_returns_the_caller_college(self):
        mine = FeeStructure.objects.create(
            college=self.college, name="Alpha tuition", amount="45000.00"
        )
        FeeStructure.objects.create(
            college=self.other_college, name="Beta tuition", amount="40000.00"
        )

        response = self.client.get("/api/fee-structures/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [mine.id])

    def test_student_cannot_create_fee_structures(self):
        self.as_student()

        response = self.client.post(
            "/api/fee-structures/",
            {"name": "Free pass", "amount": "0.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(FeeStructure.objects.exists())


class InvoiceApiTests(ERPAPITestCase):
    def setUp(self):
        super().setUp()
        self.fee = FeeStructure.objects.create(
            college=self.college, name="Tuition 2026", amount="45000.00"
        )
        self.other_fee = FeeStructure.objects.create(
            college=self.other_college, name="Beta tuition", amount="40000.00"
        )

    def create_invoice(self, college, student, fee, status="pending"):
        return Invoice.objects.create(
            college=college,
            student=student,
            fee_structure=fee,
            amount=fee.amount,
            due_date="2026-12-31",
            status=status,
        )

    def test_create_sets_college_and_accepts_own_records(self):
        response = self.client.post(
            "/api/invoices/",
            {
                "student": self.campus.student.id,
                "fee_structure": self.fee.id,
                "amount": "45000.00",
                "due_date": "2026-12-31",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        invoice = Invoice.objects.get(pk=response.data["id"])
        self.assertEqual(invoice.college, self.college)

    def test_create_rejects_student_from_another_college(self):
        response = self.client.post(
            "/api/invoices/",
            {
                "student": self.other.student.id,
                "fee_structure": self.fee.id,
                "amount": "45000.00",
                "due_date": "2026-12-31",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Invoice.objects.exists())

    def test_create_rejects_fee_structure_from_another_college(self):
        response = self.client.post(
            "/api/invoices/",
            {
                "student": self.campus.student.id,
                "fee_structure": self.other_fee.id,
                "amount": "40000.00",
                "due_date": "2026-12-31",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Invoice.objects.exists())

    def test_list_is_scoped_to_the_college(self):
        mine = self.create_invoice(
            self.college, self.campus.student, self.fee
        )
        self.create_invoice(self.other_college, self.other.student, self.other_fee)

        response = self.client.get("/api/invoices/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [mine.id])

    def test_student_only_sees_their_own_invoices(self):
        mine = self.create_invoice(self.college, self.campus.student, self.fee)
        _, other_student = self.add_student("invoice")
        self.create_invoice(self.college, other_student, self.fee)
        self.as_student()

        response = self.client.get("/api/invoices/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [mine.id])


class PaymentApiTests(ERPAPITestCase):
    def setUp(self):
        super().setUp()
        fee = FeeStructure.objects.create(
            college=self.college, name="Tuition 2026", amount="45000.00"
        )
        self.invoice = Invoice.objects.create(
            college=self.college,
            student=self.campus.student,
            fee_structure=fee,
            amount="45000.00",
            due_date="2026-12-31",
            status="pending",
        )

    def test_create_records_the_acting_user(self):
        response = self.client.post(
            "/api/payments/",
            {
                "invoice": self.invoice.id,
                "amount": "20000.00",
                "method": "upi",
                "reference": "UPI-123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        payment = Payment.objects.get(pk=response.data["id"])
        self.assertEqual(payment.recorded_by, self.admin)
        self.assertEqual(payment.amount, 20000)

    def test_create_rejects_invoice_from_another_college(self):
        other_fee = FeeStructure.objects.create(
            college=self.other_college, name="Beta tuition", amount="40000.00"
        )
        other_invoice = Invoice.objects.create(
            college=self.other_college,
            student=self.other.student,
            fee_structure=other_fee,
            amount="40000.00",
            due_date="2026-12-31",
        )

        response = self.client.post(
            "/api/payments/",
            {"invoice": other_invoice.id, "amount": "10000.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Payment.objects.exists())

    def test_list_is_scoped_to_the_college(self):
        mine = Payment.objects.create(invoice=self.invoice, amount="10000.00")

        response = self.client.get("/api/payments/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [mine.id])
