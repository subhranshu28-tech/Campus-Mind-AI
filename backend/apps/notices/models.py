from django.conf import settings
from django.db import models
from django.utils import timezone


class NoticeAudience(models.TextChoices):
    ALL = "all", "Everyone"
    STUDENTS = "students", "Students"
    FACULTY = "faculty", "Faculty"
    MANAGERS = "managers", "Managers"


class Notice(models.Model):
    college = models.ForeignKey("accounts.College", on_delete=models.CASCADE, related_name="notices")
    title = models.CharField(max_length=160)
    body = models.TextField()
    audience = models.CharField(max_length=20, choices=NoticeAudience.choices, default=NoticeAudience.ALL)
    is_pinned = models.BooleanField(default=False)
    published_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-published_at", "-id"]
        indexes = [models.Index(fields=["college", "-published_at"], name="notice_college_published_idx")]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.expires_at and self.expires_at <= self.published_at:
            raise ValidationError({"expires_at": "Expiry must be after publication."})

    def __str__(self):
        return self.title


class CampusEvent(models.Model):
    college = models.ForeignKey("accounts.College", on_delete=models.CASCADE, related_name="campus_events")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=160, blank=True)
    audience = models.CharField(max_length=20, choices=NoticeAudience.choices, default=NoticeAudience.ALL)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at", "id"]
        indexes = [models.Index(fields=["college", "starts_at"], name="event_college_starts_idx")]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "Event end must be after its start."})

    def __str__(self):
        return self.title