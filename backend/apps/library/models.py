from django.db import models


class Book(models.Model):
    college = models.ForeignKey("accounts.College", on_delete=models.CASCADE, related_name="books")
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=160, blank=True)
    isbn = models.CharField(max_length=20, blank=True)
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class BookIssue(models.Model):
    STATUS_CHOICES = [("issued", "Issued"), ("returned", "Returned"), ("overdue", "Overdue")]
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="issues")
    student = models.ForeignKey("campus.Student", on_delete=models.CASCADE, related_name="book_issues")
    issued_on = models.DateField(auto_now_add=True)
    due_on = models.DateField()
    returned_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="issued")
    fine = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        ordering = ["-issued_on"]

    def __str__(self):
        return f"{self.book} -> {self.student}"
