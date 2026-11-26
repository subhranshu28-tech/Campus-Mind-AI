from rest_framework import viewsets

from apps.accounts.tenancy import scope_queryset
from .models import Hostel, HostelAllocation, HostelRoom
from .serializers import HostelAllocationSerializer, HostelRoomSerializer, HostelSerializer


class HostelViewSet(viewsets.ModelViewSet):
    queryset = Hostel.objects.all()
    serializer_class = HostelSerializer

    def get_queryset(self):
        return scope_queryset(self.queryset, self.request.user)


class HostelRoomViewSet(viewsets.ModelViewSet):
    queryset = HostelRoom.objects.all()
    serializer_class = HostelRoomSerializer

    def get_queryset(self):
        return scope_queryset(self.queryset, self.request.user)


class HostelAllocationViewSet(viewsets.ModelViewSet):
    queryset = HostelAllocation.objects.all()
    serializer_class = HostelAllocationSerializer

    def get_queryset(self):
        return scope_queryset(self.queryset, self.request.user)
