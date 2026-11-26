from rest_framework import serializers

from apps.accounts.serializers import TenantScopedUniqueNameMixin

from .models import Company, JobPosting, PlacementApplication


class CompanySerializer(TenantScopedUniqueNameMixin, serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"
        read_only_fields = ("college",)


class JobPostingSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = JobPosting
        fields = (
            "id", "company", "company_name", "title", "description", "eligibility",
            "package", "deadline", "is_active", "created_at",
        )


class PlacementApplicationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)

    class Meta:
        model = PlacementApplication
        fields = (
            "id", "job", "job_title", "student", "student_name", "status",
            "applied_on", "remarks",
        )
        read_only_fields = ("applied_on",)


class StudentPlacementApplicationSerializer(serializers.ModelSerializer):
    """Self-service serializer: students cannot choose their own status."""

    job_title = serializers.CharField(source="job.title", read_only=True)
    company_name = serializers.CharField(source="job.company.name", read_only=True)

    class Meta:
        model = PlacementApplication
        fields = ("id", "job", "job_title", "company_name", "status", "applied_on", "remarks")
        read_only_fields = ("id", "status", "applied_on")
