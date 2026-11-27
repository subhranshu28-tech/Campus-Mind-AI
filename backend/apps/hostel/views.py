from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import ValidationError

from apps.accounts.viewsets import TenantModelViewSet

from .models import Hostel, HostelAllocation, HostelRoom
from .serializers import HostelAllocationSerializer, HostelRoomSerializer, HostelSerializer


def _sync_room_occupancy(room_id):
    if room_id is None:
        return
    count = HostelAllocation.objects.filter(room_id=room_id, is_active=True).count()
    HostelRoom.objects.filter(pk=room_id).update(occupied=count)


class HostelViewSet(TenantModelViewSet):
    queryset = Hostel.objects.all()
    serializer_class = HostelSerializer


class HostelRoomViewSet(TenantModelViewSet):
    queryset = HostelRoom.objects.select_related("hostel")
    serializer_class = HostelRoomSerializer

    def perform_destroy(self, instance):
        if instance.allocations.filter(is_active=True).exists():
            raise ValidationError({"detail": "Rooms with active allocations cannot be deleted."})
        super().perform_destroy(instance)


class HostelAllocationViewSet(TenantModelViewSet):
    queryset = HostelAllocation.objects.select_related("student__user", "room__hostel")
    serializer_class = HostelAllocationSerializer
    student_scope_field = "student_id"

    def perform_create(self, serializer):
        with transaction.atomic():
            room = HostelRoom.objects.select_for_update().get(pk=serializer.validated_data["room"].pk)
            active = room.allocations.filter(is_active=True).count()
            if active >= room.capacity:
                raise ValidationError({"room": "This room is already at full capacity."})
            student = serializer.validated_data["student"]
            if HostelAllocation.objects.filter(student=student, is_active=True).exists():
                raise ValidationError({"student": "Student already has an active hostel allocation."})
            super().perform_create(serializer)
            _sync_room_occupancy(room.pk)

    def perform_update(self, serializer):
        with transaction.atomic():
            instance = HostelAllocation.objects.select_for_update().get(pk=serializer.instance.pk)
            old_room_id = instance.room_id
            old_active = instance.is_active
            super().perform_update(serializer)
            instance = serializer.instance
            if old_room_id != instance.room_id or old_active != instance.is_active:
                _sync_room_occupancy(old_room_id)
                _sync_room_occupancy(instance.room_id)
            else:
                _sync_room_occupancy(instance.room_id)

    def perform_destroy(self, instance):
        with transaction.atomic():
            room_id = instance.room_id
            super().perform_destroy(instance)
            _sync_room_occupancy(room_id)
