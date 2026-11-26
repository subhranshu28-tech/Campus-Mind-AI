from rest_framework import serializers

from apps.accounts.serializers import TenantScopedUniqueNameMixin

from .models import Hostel, HostelAllocation, HostelRoom


class HostelSerializer(TenantScopedUniqueNameMixin, serializers.ModelSerializer):
    class Meta:
        model = Hostel
        fields = "__all__"
        read_only_fields = ("college",)


class HostelRoomSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)

    class Meta:
        model = HostelRoom
        fields = ("id", "hostel", "hostel_name", "room_number", "capacity", "occupied")


class HostelAllocationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    room_label = serializers.SerializerMethodField()

    class Meta:
        model = HostelAllocation
        fields = (
            "id", "student", "student_name", "room", "room_label", "allocated_on",
            "vacated_on", "is_active",
        )

    def get_room_label(self, obj):
        return f"{obj.room.hostel.name} · {obj.room.room_number}" if obj.room_id else ""
