from apps.accounts.viewsets import TenantModelViewSet

from .models import StudentTransport, TransportRoute, Vehicle
from .serializers import StudentTransportSerializer, TransportRouteSerializer, VehicleSerializer


class TransportRouteViewSet(TenantModelViewSet):
    queryset = TransportRoute.objects.all()
    serializer_class = TransportRouteSerializer


class VehicleViewSet(TenantModelViewSet):
    queryset = Vehicle.objects.select_related("route").order_by("registration_number")
    serializer_class = VehicleSerializer


class StudentTransportViewSet(TenantModelViewSet):
    queryset = StudentTransport.objects.select_related("student", "route").order_by(
        "-allocated_on", "-id"
    )
    serializer_class = StudentTransportSerializer
    student_scope_field = "student_id"
