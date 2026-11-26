from django.conf import settings
from django.db import models
from django.utils import timezone


class Assignment(models.Model):
    college = models.ForeignKey("accounts.College", on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    subject = models.ForeignKey("campus.Subject", on_delete=models.CASCADE, related_name="assignments")
    section = models.ForeignKey("campus.Section", on_delete=models.CASCADE, related_name="assignments")
    faculty = models.ForeignKey("campus.Faculty", on_delete=models.CASCADE, related_name="assignments")
    due_at = models.DateTimeField()
    max_marks = models.PositiveIntegerField(default=100)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-due_at", "-id"]
        indexes = [models.Index(fields=["college", "due_at"], name="assignment_college_due_idx")]

    def __str__(self):
        return self.title


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey("campus.Student", on_delete=models.CASCADE, related_name="submissions")
    file = models.FileField(upload_to="assignments/%Y/%m/", blank=True, null=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    marks = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("assignment", "student")
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.student} - {self.assignment}"
