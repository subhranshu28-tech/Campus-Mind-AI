from rest_framework import viewsets

from apps.accounts.tenancy import scope_queryset
from .models import Company, JobPosting, PlacementApplication
from .serializers import CompanySerializer, JobPostingSerializer, PlacementApplicationSerializer


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

    def get_queryset(self):
        return scope_queryset(self.queryset, self.request.user)


class JobPostingViewSet(viewsets.ModelViewSet):
    queryset = JobPosting.objects.all()
    serializer_class = JobPostingSerializer

    def get_queryset(self):
        return scope_queryset(self.queryset, self.request.user)


class PlacementApplicationViewSet(viewsets.ModelViewSet):
    queryset = PlacementApplication.objects.all()
    serializer_class = PlacementApplicationSerializer

    def get_queryset(self):
        return scope_queryset(self.queryset, self.request.user)
