from django.conf import settings
from django.db import models


class FacultyLeave(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    faculty = models.ForeignKey("campus.Faculty", on_delete=models.CASCADE, related_name="leaves")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=240, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")), name="leave_end_not_before_start"),
        ]

    def __str__(self):
        return f"{self.faculty} {self.start_date}→{self.end_date} ({self.status})"


class Substitution(models.Model):
    class Status(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        CANCELLED = "cancelled", "Cancelled"

    leave = models.ForeignKey(FacultyLeave, on_delete=models.CASCADE, related_name="substitutions")
    timetable_entry = models.ForeignKey(
        "campus.TimetableEntry", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    section = models.ForeignKey("campus.Section", on_delete=models.PROTECT, related_name="+")
    subject = models.ForeignKey("campus.Subject", on_delete=models.PROTECT, related_name="+")
    room = models.ForeignKey("campus.Classroom", on_delete=models.PROTECT, related_name="+")
    original_faculty = models.ForeignKey("campus.Faculty", on_delete=models.PROTECT, related_name="cover_given_up")
    substitute = models.ForeignKey("campus.Faculty", on_delete=models.PROTECT, related_name="cover_assignments")
    date = models.DateField()
    period = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ASSIGNED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "period"]
        indexes = [models.Index(fields=["date", "period"], name="ops_sub_date_period_idx")]
        constraints = [
            models.UniqueConstraint(
                fields=["substitute", "date", "period"], condition=models.Q(status="assigned"),
                name="unique_active_substitute_slot",
            ),
            models.UniqueConstraint(
                fields=["section", "date", "period"], condition=models.Q(status="assigned"),
                name="unique_active_cover_section_slot",
            ),
        ]

    def __str__(self):
        return f"{self.subject} {self.date} P{self.period}: {self.substitute}"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=120)
    message = models.CharField(max_length=400)
    kind = models.CharField(max_length=30, default="info")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read"], name="ops_notif_user_read_idx")]


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(max_length=60)
    entity = models.CharField(max_length=60)
    entity_id = models.CharField(max_length=40, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
