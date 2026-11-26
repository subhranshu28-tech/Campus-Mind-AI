from rest_framework import viewsets

from apps.accounts.tenancy import scope_queryset
from .models import Assignment, Submission
from .serializers import AssignmentSerializer, SubmissionSerializer


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer

    def get_queryset(self):
        return scope_queryset(self.queryset, self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer

    def get_queryset(self):
        return scope_queryset(self.queryset, self.request.user)
