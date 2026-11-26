from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated

from apps.accounts.viewsets import TenantModelViewSet

from .models import Company, JobPosting, PlacementApplication
from .serializers import (
    CompanySerializer,
    JobPostingSerializer,
    PlacementApplicationSerializer,
    StudentPlacementApplicationSerializer,
)


class CompanyViewSet(TenantModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer


class JobPostingViewSet(TenantModelViewSet):
    queryset = JobPosting.objects.select_related("company")
    serializer_class = JobPostingSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self.request.user, "role", None) == "student":
            today = timezone.localdate()
            queryset = queryset.filter(is_active=True).filter(
                Q(deadline__isnull=True) | Q(deadline__gte=today)
            )
        return queryset


class PlacementApplicationViewSet(TenantModelViewSet):
    queryset = PlacementApplication.objects.select_related("job", "student")
    serializer_class = PlacementApplicationSerializer
    write_roles = {"super_admin", "college_admin", "hod", "faculty"}
    student_scope_field = "student_id"

    def get_serializer_class(self):
        if getattr(self.request.user, "role", None) == "student":
            return StudentPlacementApplicationSerializer
        return PlacementApplicationSerializer

    def student_may_write(self, request):
        return request.method == "POST"

    def perform_create(self, serializer):
        user = self.request.user
        if getattr(user, "role", None) == "student":
            student = self.get_student_profile()
            job = serializer.validated_data.get("job")
            if job is None:
                raise ValidationError({"job": "This field is required."})
            if job.company.college_id != getattr(user, "college_id", None):
                raise ValidationError(
                    {"job": "Related records must belong to your college."}
                )
            if not job.is_active:
                raise ValidationError(
                    {"job": "This job posting is no longer accepting applications."}
                )
            if job.deadline is not None and job.deadline < timezone.localdate():
                raise ValidationError(
                    {"job": "The application deadline for this job has passed."}
                )
            if PlacementApplication.objects.filter(job=job, student=student).exists():
                raise ValidationError(
                    {"detail": "You have already applied to this job posting."}
                )
            serializer.save(student=student)
        else:
            if "student" not in serializer.validated_data:
                raise ValidationError({"student": "This field is required."})
            super().perform_create(serializer)
