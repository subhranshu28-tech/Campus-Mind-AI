from django.conf import settings
from django.db import models


class Company(models.Model):
    college = models.ForeignKey("accounts.College", on_delete=models.CASCADE, related_name="companies")
    name = models.CharField(max_length=200)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=120, blank=True)
    contact_person = models.CharField(max_length=160, blank=True)
    contact_email = models.EmailField(blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("college", "name")

    def __str__(self):
        return self.name


class JobPosting(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="job_postings")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    eligibility = models.TextField(blank=True)
    package = models.CharField(max_length=80, blank=True)
    deadline = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class PlacementApplication(models.Model):
    STATUS_CHOICES = [("applied", "Applied"), ("shortlisted", "Shortlisted"), ("selected", "Selected"), ("rejected", "Rejected")]
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name="applications")
    student = models.ForeignKey("campus.Student", on_delete=models.CASCADE, related_name="placement_applications")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="applied")
    applied_on = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = ("job", "student")
        ordering = ["-applied_on"]

    def __str__(self):
        return f"{self.student} - {self.job}"
