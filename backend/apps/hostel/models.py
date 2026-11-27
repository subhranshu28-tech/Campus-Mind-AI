from django.core.exceptions import ValidationError
from django.db import models


class Hostel(models.Model):
    college = models.ForeignKey("accounts.College", on_delete=models.CASCADE, related_name="hostels")
    name = models.CharField(max_length=160)
    gender = models.CharField(max_length=20, choices=[("male", "Male"), ("female", "Female"), ("mixed", "Mixed")], default="mixed")
    capacity = models.PositiveIntegerField(default=0)
    warden = models.CharField(max_length=160, blank=True)

    class Meta:
        ordering = ["name", "id"]
        unique_together = ("college", "name")

    def __str__(self):
        return self.name


class HostelRoom(models.Model):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="rooms")
    room_number = models.CharField(max_length=20)
    capacity = models.PositiveIntegerField(default=1)
    occupied = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("hostel", "room_number")
        ordering = ["hostel__name", "room_number", "id"]

    def clean(self):
        errors = {}
        if self.capacity < 1:
            errors["capacity"] = "Room capacity must be at least 1."
        if self.occupied > self.capacity:
            errors["occupied"] = "Occupied beds cannot exceed room capacity."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.hostel} - {self.room_number}"


class HostelAllocation(models.Model):
    student = models.ForeignKey("campus.Student", on_delete=models.CASCADE, related_name="hostel_allocations")
    room = models.ForeignKey(HostelRoom, on_delete=models.CASCADE, related_name="allocations")
    allocated_on = models.DateField(auto_now_add=True)
    vacated_on = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-allocated_on", "-id"]

    def clean(self):
        errors = {}
        if self.is_active and self.vacated_on:
            errors["vacated_on"] = "Active allocations cannot have a vacated date."
        if (not self.is_active) and not self.vacated_on:
            # allow view to auto-fill
            pass
        if self.student_id and self.is_active:
            qs = HostelAllocation.objects.filter(student_id=self.student_id, is_active=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                errors["student"] = "Student already has an active hostel allocation."
        if self.room_id and self.is_active:
            room = self.room
            active = room.allocations.filter(is_active=True)
            if self.pk:
                active = active.exclude(pk=self.pk)
            if active.count() >= room.capacity:
                errors["room"] = "This room is already at full capacity."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.student} -> {self.room}"
