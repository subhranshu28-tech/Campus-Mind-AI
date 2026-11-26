from rest_framework import serializers

from .models import Company, JobPosting, PlacementApplication


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"


class JobPostingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = "__all__"


class PlacementApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlacementApplication
        fields = "__all__"
        read_only_fields = ("applied_on",)
