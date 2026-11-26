from rest_framework import viewsets

from apps.accounts.tenancy import scope_queryset
from .models import StudentTransport, TransportRoute, Vehicle
from .serializers import StudentTransportSerializer, TransportRouteSerializer, VehicleSerializer


class TransportRouteViewSet(viewsets.ModelViewSet):
    queryset = TransportRoute.objects.all()
    serializer_class = TransportRouteSerializer

    def get_queryset(self):
        return scope_queryset(self.queryset, self.request.user)


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer

    def get_queryset(self):
        return scope_queryset(self.queryset, self.request.user)


class StudentTransportViewSet(viewsets.ModelViewSet):
    queryset = StudentTransport.objects.all()
    serializer_class = StudentTransportSerializer

    def get_queryset(self):
        return scope_queryset(self.queryset, self.request.user)
