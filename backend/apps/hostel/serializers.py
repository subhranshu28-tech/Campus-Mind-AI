from rest_framework import serializers

from .models import Hostel, HostelAllocation, HostelRoom


class HostelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hostel
        fields = "__all__"


class HostelRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelRoom
        fields = "__all__"


class HostelAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelAllocation
        fields = "__all__"
