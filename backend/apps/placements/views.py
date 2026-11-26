from apps.accounts.viewsets import TenantModelViewSet

from .models import Company, JobPosting, PlacementApplication
from .serializers import (
    CompanySerializer,
    JobPostingSerializer,
    PlacementApplicationSerializer,
)


class CompanyViewSet(TenantModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer


class JobPostingViewSet(TenantModelViewSet):
    queryset = JobPosting.objects.select_related("company")
    serializer_class = JobPostingSerializer


class PlacementApplicationViewSet(TenantModelViewSet):
    queryset = PlacementApplication.objects.select_related("job", "student")
    serializer_class = PlacementApplicationSerializer
    student_scope_field = "student_id"
