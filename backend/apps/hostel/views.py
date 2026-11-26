from apps.accounts.viewsets import TenantModelViewSet

from .models import Hostel, HostelAllocation, HostelRoom
from .serializers import HostelAllocationSerializer, HostelRoomSerializer, HostelSerializer


class HostelViewSet(TenantModelViewSet):
    queryset = Hostel.objects.all()
    serializer_class = HostelSerializer


class HostelRoomViewSet(TenantModelViewSet):
    queryset = HostelRoom.objects.select_related("hostel")
    serializer_class = HostelRoomSerializer


class HostelAllocationViewSet(TenantModelViewSet):
    queryset = HostelAllocation.objects.select_related("student", "room")
    serializer_class = HostelAllocationSerializer
    student_scope_field = "student_id"
