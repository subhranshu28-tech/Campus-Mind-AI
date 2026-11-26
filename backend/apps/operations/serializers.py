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
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "End date cannot be before the start date."})
        faculty = attrs.get("faculty", getattr(self.instance, "faculty", None))
        if faculty and start and end:
            overlapping = FacultyLeave.objects.filter(
                faculty=faculty,
                status__in=[FacultyLeave.Status.PENDING, FacultyLeave.Status.APPROVED],
                start_date__lte=end,
                end_date__gte=start,
            )
            if self.instance:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            if overlapping.exists():
                raise serializers.ValidationError(
                    {"start_date": "This faculty member already has a pending or approved leave in that period."}
                )
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
        fields = ("id", "actor_name", "action", "entity", "entity_id", "detail", "college", "created_at")

    def get_actor_name(self, obj):
        return (obj.actor.get_full_name() or obj.actor.username) if obj.actor else "System"


class ManualCoverSerializer(serializers.Serializer):
    timetable_entry = serializers.IntegerField()
    date = serializers.DateField()
    faculty = serializers.PrimaryKeyRelatedField(queryset=Faculty.objects.select_related("user"))


class MoveSerializer(serializers.Serializer):
    weekday = serializers.IntegerField(min_value=0, max_value=6)
    period = serializers.IntegerField(min_value=1, max_value=12)
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
