from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify


class College(models.Model):
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    code = models.CharField(max_length=24, unique=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        COLLEGE_ADMIN = "college_admin", "College Admin"
        HOD = "hod", "HOD"
        FACULTY = "faculty", "Faculty"
        STUDENT = "student", "Student"
        PARENT = "parent", "Parent"
        LIBRARIAN = "librarian", "Librarian"
        ACCOUNTANT = "accountant", "Accountant"
        HOSTEL_WARDEN = "hostel_warden", "Hostel Warden"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    college = models.ForeignKey("accounts.College", null=True, blank=True, on_delete=models.PROTECT, related_name="users")
    updated_at = models.DateTimeField(auto_now=True)

    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.get_full_name() or self.username
