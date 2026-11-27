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
        read_only_fields = ("occupied",)

    def validate_capacity(self, value):
        if value < 1:
            raise serializers.ValidationError("Room capacity must be at least 1.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = getattr(self, "instance", None)
        capacity = attrs.get("capacity", getattr(instance, "capacity", 1))
        if instance is not None and capacity < instance.occupied:
            raise serializers.ValidationError({"capacity": "Capacity cannot be less than current occupancy."})
        return attrs


class HostelAllocationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    room_label = serializers.SerializerMethodField()

    class Meta:
        model = HostelAllocation
        fields = (
            "id", "student", "student_name", "room", "room_label", "allocated_on",
            "vacated_on", "is_active",
        )
        read_only_fields = ("allocated_on",)

    def get_room_label(self, obj):
        return f"{obj.room.hostel.name} · {obj.room.room_number}" if obj.room_id else ""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = getattr(self, "instance", None)
        is_active = attrs.get("is_active", getattr(instance, "is_active", True))
        vacated_on = attrs.get("vacated_on", getattr(instance, "vacated_on", None))
        student = attrs.get("student", getattr(instance, "student", None))
        room = attrs.get("room", getattr(instance, "room", None))
        if is_active and vacated_on:
            raise serializers.ValidationError({"vacated_on": "Active allocations cannot have a vacated date."})
        if (not is_active) and not vacated_on:
            from django.utils import timezone
            attrs["vacated_on"] = timezone.localdate()
        if is_active and student is not None:
            qs = HostelAllocation.objects.filter(student=student, is_active=True)
            if instance is not None:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"student": "Student already has an active hostel allocation."})
        if is_active and room is not None:
            active = room.allocations.filter(is_active=True)
            if instance is not None:
                active = active.exclude(pk=instance.pk)
            if active.count() >= room.capacity:
                raise serializers.ValidationError({"room": "This room is already at full capacity."})
        return attrs
