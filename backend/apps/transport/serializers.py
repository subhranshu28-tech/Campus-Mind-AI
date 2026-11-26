from rest_framework import serializers

from .models import StudentTransport, TransportRoute, Vehicle


class TransportRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportRoute
        fields = "__all__"


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = "__all__"


class StudentTransportSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentTransport
        fields = "__all__"
