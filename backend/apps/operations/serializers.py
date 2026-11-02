from rest_framework import serializers

from apps.campus.models import Classroom, Faculty, Semester

from .models import AuditLog, FacultyLeave, Notification, Substitution


def _faculty_name(faculty):
    return faculty.user.get_full_name() or faculty.user.username


class FacultyLeaveSerializer(serializers.ModelSerializer):
    faculty_name = serializers.SerializerMethodField()
    covered = serializers.SerializerMethodField()

    class Meta:
        model = FacultyLeave
        fields = ("id", "faculty", "faculty_name", "start_date", "end_date", "reason", "status", "decided_at", "created_at", "covered")
        read_only_fields = ("status", "decided_at", "created_at")
        extra_kwargs = {"faculty": {"required": False}}

    def get_faculty_name(self, obj):
        return _faculty_name(obj.faculty)

    def get_covered(self, obj):
        return obj.substitutions.filter(status="assigned").count()

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError({"end_date": "End date cannot be before the start date."})
        return attrs


class SubstitutionSerializer(serializers.ModelSerializer):
    subject_code = serializers.CharField(source="subject.code", read_only=True)
    section_name = serializers.CharField(source="section.__str__", read_only=True)
    room_code = serializers.CharField(source="room.code", read_only=True)
    original_name = serializers.SerializerMethodField()
    substitute_name = serializers.SerializerMethodField()

    class Meta:
        model = Substitution
        fields = ("id", "leave", "date", "period", "status", "subject_code", "section_name", "room_code", "original_name", "substitute_name")

    def get_original_name(self, obj):
        return _faculty_name(obj.original_faculty)

    def get_substitute_name(self, obj):
        return _faculty_name(obj.substitute)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "title", "message", "kind", "is_read", "created_at")


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ("id", "actor_name", "action", "entity", "entity_id", "detail", "created_at")

    def get_actor_name(self, obj):
        return (obj.actor.get_full_name() or obj.actor.username) if obj.actor else "System"


class ManualCoverSerializer(serializers.Serializer):
    timetable_entry = serializers.IntegerField()
    date = serializers.DateField()
    faculty = serializers.PrimaryKeyRelatedField(queryset=Faculty.objects.select_related("user"))


class MoveSerializer(serializers.Serializer):
    weekday = serializers.IntegerField(min_value=0, max_value=4)
    period = serializers.IntegerField(min_value=1, max_value=8)
    room = serializers.PrimaryKeyRelatedField(queryset=Classroom.objects.all())
    dry_run = serializers.BooleanField(default=False)


class AutoExamSerializer(serializers.Serializer):
    semester = serializers.PrimaryKeyRelatedField(queryset=Semester.objects.all())
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    holidays = serializers.ListField(child=serializers.DateField(), required=False, default=list)
    avoid_class_clashes = serializers.BooleanField(default=False)
    replace_existing = serializers.BooleanField(default=True)
    preview = serializers.BooleanField(default=True)

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError({"end_date": "End date cannot be before the start date."})
        return attrs
