from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.viewsets import TenantModelViewSet

from .models import Assignment, Submission
from .serializers import (
    AssignmentSerializer,
    StudentSubmissionSerializer,
    SubmissionSerializer,
)


class AssignmentViewSet(TenantModelViewSet):
    queryset = Assignment.objects.select_related("subject", "section", "faculty")
    serializer_class = AssignmentSerializer
    write_roles = {"super_admin", "college_admin", "hod", "faculty"}
    student_scope_field = "section_id"
    student_scope_by = "section"

    def get_create_kwargs(self):
        return {"created_by": self.request.user}


class SubmissionViewSet(TenantModelViewSet):
    queryset = Submission.objects.select_related("assignment", "student")
    serializer_class = SubmissionSerializer
    write_roles = {"super_admin", "college_admin", "hod", "faculty"}
    student_scope_field = "student_id"

    def get_serializer_class(self):
        if getattr(self.request.user, "role", None) == "student":
            return StudentSubmissionSerializer
        return SubmissionSerializer

    def student_may_write(self, request):
        return request.method == "POST"

    def perform_create(self, serializer):
        user = self.request.user
        if getattr(user, "role", None) == "student":
            student = self.get_student_profile()
            assignment = serializer.validated_data.get("assignment")
            if assignment is None:
                raise ValidationError({"assignment": "This field is required."})
            if assignment.college_id != getattr(user, "college_id", None):
                raise ValidationError(
                    {"assignment": "Related records must belong to your college."}
                )
            if assignment.section_id != student.section_id:
                raise ValidationError(
                    {"assignment": "You can only submit assignments for your section."}
                )
            if Submission.objects.filter(
                assignment=assignment, student=student
            ).exists():
                raise ValidationError(
                    {"detail": "You have already submitted this assignment."}
                )
            serializer.save(student=student)
        else:
            if "student" not in serializer.validated_data:
                raise ValidationError({"student": "This field is required."})
            super().perform_create(serializer)
