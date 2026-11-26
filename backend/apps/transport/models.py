from django.db import models


class TransportRoute(models.Model):
    college = models.ForeignKey("accounts.College", on_delete=models.CASCADE, related_name="transport_routes")
    name = models.CharField(max_length=160)
    origin = models.CharField(max_length=160, blank=True)
    destination = models.CharField(max_length=160, blank=True)
    fare = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        ordering = ["name"]
        unique_together = ("college", "name")

    def __str__(self):
        return self.name


class Vehicle(models.Model):
    route = models.ForeignKey(TransportRoute, on_delete=models.SET_NULL, null=True, blank=True, related_name="vehicles")
    registration_number = models.CharField(max_length=30, unique=True)
    capacity = models.PositiveIntegerField(default=0)
    driver_name = models.CharField(max_length=160, blank=True)
    driver_phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.registration_number


class StudentTransport(models.Model):
    student = models.ForeignKey("campus.Student", on_delete=models.CASCADE, related_name="transport_allocations")
    route = models.ForeignKey(TransportRoute, on_delete=models.CASCADE, related_name="students")
    pickup_point = models.CharField(max_length=160, blank=True)
    allocated_on = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("student", "route")

    def __str__(self):
        return f"{self.student} -> {self.route}"
