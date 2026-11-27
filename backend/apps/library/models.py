from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Book(models.Model):
    college = models.ForeignKey("accounts.College", on_delete=models.CASCADE, related_name="books")
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=160, blank=True)
    isbn = models.CharField(max_length=20, blank=True)
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title", "id"]

    def clean(self):
        errors = {}
        if self.total_copies < 1:
            errors["total_copies"] = "Total copies must be at least 1."
        if self.available_copies > self.total_copies:
            errors["available_copies"] = "Available copies cannot exceed total copies."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.title


class BookIssue(models.Model):
    class Status(models.TextChoices):
        ISSUED = "issued", "Issued"
        RETURNED = "returned", "Returned"
        OVERDUE = "overdue", "Overdue"

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="issues")
    student = models.ForeignKey("campus.Student", on_delete=models.CASCADE, related_name="book_issues")
    issued_on = models.DateField(auto_now_add=True)
    due_on = models.DateField()
    returned_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ISSUED)
    fine = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["-issued_on", "-id"]

    def clean(self):
        errors = {}
        if self.returned_on and self.issued_on and self.returned_on < self.issued_on:
            errors["returned_on"] = "Return date cannot be before issue date."
        if self.fine is not None and self.fine < 0:
            errors["fine"] = "Fine cannot be negative."
        if self.status == self.Status.RETURNED and not self.returned_on:
            pass
        if self.status in {self.Status.ISSUED, self.Status.OVERDUE} and self.returned_on:
            errors["returned_on"] = "Returned date is only valid for returned issues."
        if errors:
            raise ValidationError(errors)

    def sync_status(self, save=True):
        if self.status == self.Status.RETURNED:
            if self.returned_on is None:
                self.returned_on = timezone.localdate()
        else:
            self.status = self.Status.OVERDUE if self.due_on < timezone.localdate() else self.Status.ISSUED
            self.returned_on = None
        if save:
            self.save(update_fields=["status", "returned_on"])
        return self

    def __str__(self):
        return f"{self.book} -> {self.student}"
