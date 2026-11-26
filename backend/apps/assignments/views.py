from apps.accounts.viewsets import TenantModelViewSet

from .models import Assignment, Submission
from .serializers import AssignmentSerializer, SubmissionSerializer


class AssignmentViewSet(TenantModelViewSet):
    queryset = Assignment.objects.select_related("subject", "section", "faculty")
    serializer_class = AssignmentSerializer
    write_roles = {"super_admin", "college_admin", "hod", "faculty"}
    # Students see the assignments published for their own section.
    student_scope_field = "section_id"
    student_scope_by = "section"

    def get_create_kwargs(self):
        return {"created_by": self.request.user}


class SubmissionViewSet(TenantModelViewSet):
    queryset = Submission.objects.select_related("assignment", "student")
    serializer_class = SubmissionSerializer
    write_roles = {"super_admin", "college_admin", "hod", "faculty"}
    student_scope_field = "student_id"
