from django.db import models


class Hostel(models.Model):
    college = models.ForeignKey("accounts.College", on_delete=models.CASCADE, related_name="hostels")
    name = models.CharField(max_length=160)
    gender = models.CharField(max_length=20, choices=[("male", "Male"), ("female", "Female"), ("mixed", "Mixed")], default="mixed")
    capacity = models.PositiveIntegerField(default=0)
    warden = models.CharField(max_length=160, blank=True)

    class Meta:
        ordering = ["name"]
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
        ordering = ["room_number"]

    def __str__(self):
        return f"{self.hostel} - {self.room_number}"


class HostelAllocation(models.Model):
    student = models.ForeignKey("campus.Student", on_delete=models.CASCADE, related_name="hostel_allocations")
    room = models.ForeignKey(HostelRoom, on_delete=models.CASCADE, related_name="allocations")
    allocated_on = models.DateField(auto_now_add=True)
    vacated_on = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-allocated_on"]

    def __str__(self):
        return f"{self.student} -> {self.room}"
