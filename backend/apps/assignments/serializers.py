from rest_framework import serializers

from .models import Assignment, Submission


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = "__all__"
        read_only_fields = ("college", "created_by", "created_at")


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = "__all__"
        read_only_fields = ("submitted_at", "graded_by", "graded_at")


class StudentSubmissionSerializer(serializers.ModelSerializer):
    """Self-service serializer for students: grading fields are read-only."""

    class Meta:
        model = Submission
        fields = (
            "id",
            "assignment",
            "file",
            "submitted_at",
            "marks",
            "feedback",
            "graded_at",
        )
        read_only_fields = ("id", "submitted_at", "marks", "feedback", "graded_at")
