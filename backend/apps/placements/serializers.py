from rest_framework import serializers

from apps.accounts.serializers import TenantScopedUniqueNameMixin

from .models import Company, JobPosting, PlacementApplication


class CompanySerializer(TenantScopedUniqueNameMixin, serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"
        read_only_fields = ("college",)


class JobPostingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = "__all__"


class PlacementApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlacementApplication
        fields = "__all__"
        read_only_fields = ("applied_on",)


class StudentPlacementApplicationSerializer(serializers.ModelSerializer):
    """Self-service serializer: students cannot choose their own status."""

    class Meta:
        model = PlacementApplication
        fields = ("id", "job", "status", "applied_on", "remarks")
        read_only_fields = ("id", "status", "applied_on")
