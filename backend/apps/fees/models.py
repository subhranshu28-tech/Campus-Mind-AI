from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


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

    def clean(self):
        if self.amount is not None and self.amount < 0:
            raise ValidationError({"amount": "Amount cannot be negative."})

    def __str__(self):
        return self.name


class Invoice(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        CANCELLED = "cancelled", "Cancelled"

    college = models.ForeignKey("accounts.College", on_delete=models.CASCADE, related_name="invoices")
    student = models.ForeignKey("campus.Student", on_delete=models.CASCADE, related_name="invoices")
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.PROTECT, related_name="invoices")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["college", "status"], name="invoice_college_status_idx")]

    def clean(self):
        errors = {}
        if self.amount is not None and self.amount <= 0:
            errors["amount"] = "Amount must be greater than zero."
        if self.status == self.Status.PAID and not self.paid_at:
            # allow save hooks to fill it
            pass
        if self.status in {self.Status.PENDING, self.Status.OVERDUE} and self.paid_at:
            errors["paid_at"] = "Paid timestamp is only valid for paid invoices."
        if errors:
            raise ValidationError(errors)

    @property
    def amount_paid(self):
        return self.payments.aggregate(total=models.Sum("amount"))["total"] or 0

    @property
    def balance(self):
        return max(self.amount - self.amount_paid, 0)

    def sync_status(self, save=True):
        paid = self.payments.aggregate(total=models.Sum("amount"))["total"] or 0
        if self.status == self.Status.CANCELLED:
            changed = False
        elif paid >= self.amount:
            changed = self.status != self.Status.PAID or self.paid_at is None
            self.status = self.Status.PAID
            self.paid_at = self.paid_at or timezone.now()
        else:
            new_status = self.Status.OVERDUE if self.due_date < timezone.localdate() else self.Status.PENDING
            changed = self.status != new_status or self.paid_at is not None
            self.status = new_status
            self.paid_at = None
        if save and changed:
            self.save(update_fields=["status", "paid_at"])
        return self

    def __str__(self):
        return f"{self.student} - {self.fee_structure}"


class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=40, default="cash")
    reference = models.CharField(max_length=120, blank=True)
    paid_on = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-paid_on", "-id"]

    def clean(self):
        errors = {}
        if self.amount is not None and self.amount <= 0:
            errors["amount"] = "Payment amount must be greater than zero."
        if self.invoice_id:
            invoice = self.invoice
            if invoice.status == Invoice.Status.CANCELLED:
                errors["invoice"] = "Cancelled invoices cannot receive payments."
            else:
                paid = invoice.payments.exclude(pk=self.pk).aggregate(total=models.Sum("amount"))["total"] or 0
                if self.amount is not None and paid + self.amount > invoice.amount:
                    errors["amount"] = "Payment exceeds the invoice balance."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.amount} for {self.invoice}"
