from rest_framework import serializers

from apps.accounts.serializers import TenantScopedUniqueNameMixin

from .models import Hostel, HostelAllocation, HostelRoom


class HostelSerializer(TenantScopedUniqueNameMixin, serializers.ModelSerializer):
    class Meta:
        model = Hostel
        fields = "__all__"
        read_only_fields = ("college",)


class HostelRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelRoom
        fields = "__all__"


class HostelAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelAllocation
        fields = "__all__"
