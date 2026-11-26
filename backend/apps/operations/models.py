import hashlib
import json

from django.conf import settings
from django.db import models
from django.utils import timezone


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
            models.CheckConstraint(
                condition=models.Q(period__gte=1, period__lte=8), name="substitution_period_valid"
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
    # The college is stored directly so logs survive actor deletion and system
    # actions with no actor can still be attributed to a tenant.
    college = models.ForeignKey(
        "accounts.College", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(max_length=60)
    entity = models.CharField(max_length=60)
    entity_id = models.CharField(max_length=40, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Tamper-evident chain: each row stores the hash of its predecessor so a
    # deleted or rewritten audit entry breaks every later hash in the chain.
    previous_hash = models.CharField(max_length=64, blank=True, default="")
    entry_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["college", "-created_at"], name="ops_audit_college_time_idx")]

    def _compute_entry_hash(self, previous_hash):
        payload = {
            "college_id": self.college_id,
            "actor_id": self.actor_id,
            "action": self.action,
            "entity": self.entity,
            "entity_id": self.entity_id,
            "detail": self.detail or {},
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "previous_hash": previous_hash,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

    def save(self, *args, **kwargs):
        creating = self._state.adding
        if not self.entry_hash:
            if self.created_at is None:
                self.created_at = timezone.now()
            previous = (
                AuditLog.objects.filter(college=self.college)
                .exclude(pk=self.pk)
                .order_by("-created_at", "-id")
                .first()
            )
            self.previous_hash = previous.entry_hash if previous and previous.entry_hash else ""
            self.entry_hash = self._compute_entry_hash(self.previous_hash)
            super().save(*args, **kwargs)
            if creating:
                self.refresh_from_db(fields=["created_at"])
                recomputed = self._compute_entry_hash(self.previous_hash)
                if recomputed != self.entry_hash:
                    self.entry_hash = recomputed
                    super().save(update_fields=["entry_hash"])
            return
        super().save(*args, **kwargs)

    @classmethod
    def verify_chain(cls, college=None):
        queryset = cls.objects.all() if college is None else cls.objects.filter(college=college)
        previous_hash = ""
        for row in queryset.order_by("created_at", "id"):
            expected = row._compute_entry_hash(previous_hash)
            if row.entry_hash and row.entry_hash != expected:
                return False
            previous_hash = row.entry_hash or previous_hash
        return True
