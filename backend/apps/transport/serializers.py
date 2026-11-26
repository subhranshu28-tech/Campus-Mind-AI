from rest_framework import serializers

from apps.accounts.serializers import TenantScopedUniqueNameMixin

from .models import StudentTransport, TransportRoute, Vehicle


class TransportRouteSerializer(TenantScopedUniqueNameMixin, serializers.ModelSerializer):
    class Meta:
        model = TransportRoute
        fields = "__all__"
        read_only_fields = ("college",)


class VehicleSerializer(serializers.ModelSerializer):
    route_name = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = (
            "id", "route", "route_name", "registration_number", "capacity",
            "driver_name", "driver_phone",
        )

    def get_route_name(self, obj):
        return obj.route.name if obj.route_id else ""


class StudentTransportSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    route_name = serializers.CharField(source="route.name", read_only=True)

    class Meta:
        model = StudentTransport
        fields = (
            "id", "student", "student_name", "route", "route_name", "pickup_point",
            "allocated_on", "is_active",
        )
