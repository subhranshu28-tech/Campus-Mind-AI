from rest_framework import serializers

from apps.accounts.serializers import TenantScopedUniqueNameMixin

from .models import StudentTransport, TransportRoute, Vehicle


class TransportRouteSerializer(TenantScopedUniqueNameMixin, serializers.ModelSerializer):
    class Meta:
        model = TransportRoute
        fields = "__all__"
        read_only_fields = ("college",)

    def validate_fare(self, value):
        if value < 0:
            raise serializers.ValidationError("Fare cannot be negative.")
        return value


class VehicleSerializer(serializers.ModelSerializer):
    route_name = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = (
            "id", "route", "route_name", "registration_number", "capacity",
            "driver_name", "driver_phone",
        )
        extra_kwargs = {"route": {"required": True, "allow_null": False}}

    def get_route_name(self, obj):
        return obj.route.name if obj.route_id else ""

    def validate_registration_number(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Registration number is required.")
        request = self.context.get("request")
        college_id = getattr(getattr(request, "user", None), "college_id", None)
        qs = Vehicle.objects.filter(registration_number__iexact=value)
        if college_id:
            qs = qs.filter(route__college_id=college_id)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A vehicle with this registration number already exists in your college.")
        return value

    def validate_capacity(self, value):
        if value < 0:
            raise serializers.ValidationError("Capacity cannot be negative.")
        return value


class StudentTransportSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    route_name = serializers.CharField(source="route.name", read_only=True)

    class Meta:
        model = StudentTransport
        fields = (
            "id", "student", "student_name", "route", "route_name", "pickup_point",
            "allocated_on", "is_active",
        )
        read_only_fields = ("allocated_on",)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = getattr(self, "instance", None)
        student = attrs.get("student", getattr(instance, "student", None))
        is_active = attrs.get("is_active", getattr(instance, "is_active", True))
        if is_active and student is not None:
            qs = StudentTransport.objects.filter(student=student, is_active=True)
            if instance is not None:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"student": "Student already has an active transport allocation."})
        return attrs
