from rest_framework.exceptions import ValidationError

from apps.accounts.tenancy import TENANT_LOOKUPS
from apps.accounts.viewsets import TenantModelViewSet

from .models import StudentTransport, TransportRoute, Vehicle
from .serializers import StudentTransportSerializer, TransportRouteSerializer, VehicleSerializer


class TransportRouteViewSet(TenantModelViewSet):
    queryset = TransportRoute.objects.all()
    serializer_class = TransportRouteSerializer


class VehicleViewSet(TenantModelViewSet):
    queryset = Vehicle.objects.select_related("route")
    serializer_class = VehicleSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        college_id = getattr(self.request.user, "college_id", None)
        if not college_id:
            return queryset.none()
        # Vehicles are tenant-owned through route. Unassigned vehicles are not visible.
        return queryset.filter(route__college_id=college_id)

    def perform_create(self, serializer):
        if not serializer.validated_data.get("route"):
            raise ValidationError({"route": "Route is required."})
        super().perform_create(serializer)

    def perform_update(self, serializer):
        if "route" in serializer.validated_data and not serializer.validated_data.get("route"):
            raise ValidationError({"route": "Route is required."})
        super().perform_update(serializer)


class StudentTransportViewSet(TenantModelViewSet):
    queryset = StudentTransport.objects.select_related("student__user", "route")
    serializer_class = StudentTransportSerializer
    student_scope_field = "student_id"
