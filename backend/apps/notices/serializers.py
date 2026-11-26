from rest_framework import serializers

from .models import CampusEvent, Notice


class NoticeSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = Notice
        fields = (
            "id", "title", "body", "audience", "is_pinned", "published_at",
            "expires_at", "created_by", "created_by_name", "created_at", "updated_at",
        )
        read_only_fields = ("created_by", "created_at", "updated_at")

    def validate(self, attrs):
        published_at = attrs.get("published_at")
        expires_at = attrs.get("expires_at")
        if expires_at and published_at and expires_at <= published_at:
            raise serializers.ValidationError({"expires_at": "Expiry must be after publication."})
        return attrs


class CampusEventSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = CampusEvent
        fields = (
            "id", "title", "description", "location", "audience", "starts_at",
            "ends_at", "created_by", "created_by_name", "created_at",
        )
        read_only_fields = ("created_by", "created_at")

    def validate(self, attrs):
        starts_at = attrs.get("starts_at")
        ends_at = attrs.get("ends_at")
        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError({"ends_at": "Event end must be after its start."})
        return attrs
