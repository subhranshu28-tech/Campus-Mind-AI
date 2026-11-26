from rest_framework import serializers

from apps.accounts.serializers import TenantScopedUniqueNameMixin

from .models import StudentTransport, TransportRoute, Vehicle


class TransportRouteSerializer(TenantScopedUniqueNameMixin, serializers.ModelSerializer):
    class Meta:
        model = TransportRoute
        fields = "__all__"
        read_only_fields = ("college",)


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = "__all__"


class StudentTransportSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentTransport
        fields = "__all__"
