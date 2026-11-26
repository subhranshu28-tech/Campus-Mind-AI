from rest_framework import serializers

from .models import Assignment, Submission


class AssignmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)
    faculty_name = serializers.CharField(source="faculty.user.get_full_name", read_only=True)

    class Meta:
        model = Assignment
        fields = (
            "id", "college", "title", "description", "subject", "subject_name",
            "section", "section_name", "faculty", "faculty_name", "due_at",
            "max_marks", "created_by", "created_at",
        )
        read_only_fields = ("college", "created_by", "created_at")


class SubmissionSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)

    class Meta:
        model = Submission
        fields = (
            "id", "assignment", "assignment_title", "student", "student_name",
            "file", "submitted_at", "marks", "feedback", "graded_by", "graded_at",
        )
        read_only_fields = ("submitted_at", "graded_by", "graded_at")


class StudentSubmissionSerializer(serializers.ModelSerializer):
    """Self-service serializer for students: grading fields are read-only."""

    assignment_title = serializers.CharField(source="assignment.title", read_only=True)

    class Meta:
        model = Submission
        fields = (
            "id",
            "assignment",
            "assignment_title",
            "file",
            "submitted_at",
            "marks",
            "feedback",
            "graded_at",
        )
        read_only_fields = ("id", "submitted_at", "marks", "feedback", "graded_at")
