from django.conf import settings
from django.db import models


class FeeStructure(models.Model):
    college = models.ForeignKey("accounts.College", on_delete=models.CASCADE, related_name="fee_structures")
    name = models.CharField(max_length=160)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("college", "name")

    def __str__(self):
        return self.name


class Invoice(models.Model):
    STATUS_CHOICES = [("pending", "Pending"), ("paid", "Paid"), ("overdue", "Overdue"), ("cancelled", "Cancelled")]
    college = models.ForeignKey("accounts.College", on_delete=models.CASCADE, related_name="invoices")
    student = models.ForeignKey("campus.Student", on_delete=models.CASCADE, related_name="invoices")
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.PROTECT, related_name="invoices")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["college", "status"], name="invoice_college_status_idx")]

    def __str__(self):
        return f"{self.student} - {self.fee_structure}"


class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=40, default="cash")
    reference = models.CharField(max_length=120, blank=True)
    paid_on = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    def __str__(self):
        return f"{self.amount} for {self.invoice}"
