from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError as ApiValidationError
from rest_framework import serializers

from .models import (
    AcademicYear,
    AttendanceRecord,
    Classroom,
    Course,
    Department,
    ExamSchedule,
    Faculty,
    FacultyAvailability,
    Section,
    Semester,
    Student,
    Subject,
    SubjectNote,
    PreviousYearQuestionPaper,
    TeachingAssignment,
    TimetableEntry,
)

User = get_user_model()


class CampusAccountSerializer(serializers.ModelSerializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "password")
        read_only_fields = ("id",)
        extra_kwargs = {
            "username": {"required": True},
            "email": {"required": True},
        }

    def validate_username(self, value):
        current_user = getattr(self.parent.instance, "user", None) if self.parent and self.parent.instance else None
        query = User.objects.filter(username=value)
        if current_user:
            query = query.exclude(pk=current_user.pk)
        if query.exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        current_user = getattr(self.parent.instance, "user", None) if self.parent and self.parent.instance else None
        query = User.objects.filter(email=value)
        if current_user:
            query = query.exclude(pk=current_user.pk)
        if query.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        if request and getattr(request.user, "college_id", None):
            validated_data["college_id"] = request.user.college_id
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "A password is required for a new account."})
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class DepartmentSerializer(serializers.ModelSerializer):
    head_name = serializers.CharField(source="head.get_full_name", read_only=True)
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = ("id", "name", "code", "head", "head_name", "student_count", "is_active", "created_at")
        read_only_fields = ("created_at",)

    def validate_head(self, user):
        if user and user.role not in {"hod", "faculty"}:
            raise serializers.ValidationError("Department head must be HOD or faculty.")
        return user


class StudentSerializer(serializers.ModelSerializer):
    user = CampusAccountSerializer()
    semester = serializers.IntegerField(min_value=1, max_value=12)
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)

    class Meta:
        model = Student
        fields = (
            "id", "user", "user_name", "student_id", "department", "department_name",
            "semester", "section", "section_name", "enrolled_on", "created_at",
        )
        read_only_fields = ("created_at",)

    @transaction.atomic
    def create(self, validated_data):
        account = validated_data.pop("user")
        account["role"] = User.Role.STUDENT
        user = CampusAccountSerializer(context=self.context).create(account)
        return Student.objects.create(user=user, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        account = validated_data.pop("user", None)
        if account:
            account.pop("username", None)
            account.pop("email", None)
            CampusAccountSerializer(instance=instance.user, context=self.context).update(
                instance.user, account
            )
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance

    def validate(self, attrs):
        attrs = super().validate(attrs)
        department = attrs.get("department", getattr(self.instance, "department", None))
        semester_number = attrs.get("semester", getattr(self.instance, "semester", None))
        section = attrs.get("section", getattr(self.instance, "section", None))
        if section and semester_number is not None and section.semester.number != semester_number:
            raise serializers.ValidationError({"section": "Section semester must match the student's semester."})
        if section and department and section.semester.course.department_id != department.id:
            raise serializers.ValidationError({"section": "Section course must belong to the student's department."})
        return attrs


class FacultySerializer(serializers.ModelSerializer):
    user = CampusAccountSerializer()
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Faculty
        fields = (
            "id", "user", "user_name", "employee_id", "department",
            "department_name", "qualification", "experience_years",
        )

    @transaction.atomic
    def create(self, validated_data):
        account = validated_data.pop("user")
        account["role"] = User.Role.FACULTY
        user = CampusAccountSerializer(context=self.context).create(account)
        return Faculty.objects.create(user=user, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        account = validated_data.pop("user", None)
        if account:
            account.pop("username", None)
            account.pop("email", None)
            CampusAccountSerializer(instance=instance.user, context=self.context).update(
                instance.user, account
            )
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ("id", "name", "starts_on", "ends_on", "is_active", "created_at")
        read_only_fields = ("created_at",)

    def validate(self, attrs):
        starts_on = attrs.get("starts_on", getattr(self.instance, "starts_on", None))
        ends_on = attrs.get("ends_on", getattr(self.instance, "ends_on", None))
        if starts_on and ends_on and ends_on <= starts_on:
            raise serializers.ValidationError({"ends_on": "End date must be after the start date."})
        return attrs


    def validate_is_active(self, value):
        college_id = getattr(getattr(self.context.get("request"), "user", None), "college_id", None)
        if value and AcademicYear.objects.filter(college_id=college_id, is_active=True).exclude(
            pk=getattr(self.instance, "pk", None)
        ).exists():
            raise serializers.ValidationError("Another academic year is already active.")
        return value


class CourseSerializer(serializers.ModelSerializer):
    duration_years = serializers.IntegerField(min_value=1, max_value=10)

    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Course
        fields = ("id", "department", "department_name", "name", "code", "duration_years", "is_active")


class SemesterSerializer(serializers.ModelSerializer):
    number = serializers.IntegerField(min_value=1, max_value=12)

    course_name = serializers.CharField(source="course.name", read_only=True)
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)

    class Meta:
        model = Semester
        fields = ("id", "course", "course_name", "academic_year", "academic_year_name", "number")


class SectionSerializer(serializers.ModelSerializer):
    semester_label = serializers.CharField(source="semester.__str__", read_only=True)
    capacity = serializers.IntegerField(min_value=1)

    class Meta:
        model = Section
        fields = ("id", "semester", "semester_label", "name", "capacity")


class SubjectSerializer(serializers.ModelSerializer):
    credits = serializers.IntegerField(min_value=1, max_value=30)

    course_name = serializers.CharField(source="course.name", read_only=True)
    semester_label = serializers.CharField(source="semester.__str__", read_only=True)

    class Meta:
        model = Subject
        fields = ("id", "course", "course_name", "semester", "semester_label", "code", "name", "is_lab", "credits")

    def validate(self, attrs):
        course = attrs.get("course", getattr(self.instance, "course", None))
        semester = attrs.get("semester", getattr(self.instance, "semester", None))
        if course and semester and semester.course_id != course.id:
            raise serializers.ValidationError({"semester": "Semester must belong to the selected course."})
        return attrs


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_id = serializers.CharField(source="student.student_id", read_only=True)
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    recorded_by_name = serializers.CharField(source="recorded_by.get_full_name", read_only=True)
    recorded_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = (
            "id", "student", "student_id", "student_name", "date", "is_present",
            "recorded_by", "recorded_by_name", "created_at",
        )
        read_only_fields = ("created_at",)

    def create(self, validated_data):
        return AttendanceRecord.objects.create(recorded_by=self.context["request"].user, **validated_data)


class SubjectNoteSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    subject_code = serializers.CharField(source="subject.code", read_only=True)
    file_name = serializers.SerializerMethodField()
    uploaded_by_id = serializers.IntegerField(read_only=True)
    uploaded_by_name = serializers.CharField(source="uploaded_by.get_full_name", read_only=True)
    file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = SubjectNote
        fields = (
            "id", "subject", "subject_name", "subject_code", "title", "description",
            "file", "file_name", "uploaded_by_id", "uploaded_by_name", "uploaded_at",
        )
        read_only_fields = ("id", "file_name", "uploaded_by_id", "uploaded_by_name", "uploaded_at")

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Enter a title for this subject resource.")
        return value.strip()

    def get_file_name(self, obj):
        return obj.file.name.rsplit("/", 1)[-1]

    def validate_file(self, uploaded_file):
        if uploaded_file.size > 20 * 1024 * 1024:
            raise serializers.ValidationError("PDF files must be 20 MB or smaller.")
        if not uploaded_file.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("Only PDF files are allowed.")
        header = uploaded_file.read(1024)
        uploaded_file.seek(0)
        if b"%PDF-" not in header:
            raise serializers.ValidationError("The uploaded file is not a valid PDF.")
        return uploaded_file

    def validate(self, attrs):
        uploaded_file = attrs.get("file")
        if uploaded_file is None and self.instance is None:
            raise serializers.ValidationError({"file": "Choose a PDF file to upload."})
        subject = attrs.get("subject", getattr(self.instance, "subject", None))
        user = self.context["request"].user
        if user.role == "faculty":
            try:
                faculty = user.faculty_record
            except ObjectDoesNotExist as error:
                raise ApiValidationError({"subject": "No faculty profile is linked to this account."}) from error
            if not TeachingAssignment.objects.filter(faculty=faculty, subject=subject).exists():
                raise ApiValidationError({"subject": "You can only upload notes for subjects assigned to you."})
        return attrs


class PreviousYearQuestionPaperSerializer(SubjectNoteSerializer):
    class Meta(SubjectNoteSerializer.Meta):
        model = PreviousYearQuestionPaper
        fields = (
            "id", "subject", "subject_name", "subject_code", "title", "exam_year",
            "description", "file", "file_name", "uploaded_by_id", "uploaded_by_name",
            "uploaded_at",
        )

    def validate_exam_year(self, value):
        if value < 1950 or value > timezone.localdate().year:
            raise serializers.ValidationError(
                f"Enter an exam year between 1950 and {timezone.localdate().year}."
            )
        return value


class ClassroomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classroom
        fields = ("id", "name", "code", "capacity", "is_lab", "is_active")

    def validate_capacity(self, value):
        if value < 1:
            raise serializers.ValidationError("Room capacity must be at least one.")
        return value


class TeachingAssignmentSerializer(serializers.ModelSerializer):
    section_label = serializers.CharField(source="section.__str__", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    faculty_name = serializers.CharField(source="faculty.user.get_full_name", read_only=True)

    class Meta:
        model = TeachingAssignment
        fields = ("id", "section", "section_label", "subject", "subject_name", "faculty", "faculty_name", "periods_per_week")

    def validate(self, attrs):
        section = attrs.get("section", getattr(self.instance, "section", None))
        subject = attrs.get("subject", getattr(self.instance, "subject", None))
        faculty = attrs.get("faculty", getattr(self.instance, "faculty", None))
        periods = attrs.get("periods_per_week", getattr(self.instance, "periods_per_week", 3))
        errors = {}
        if section and subject and section.semester_id != subject.semester_id:
            errors["subject"] = "Subject must belong to the section's semester."
        if faculty and subject and faculty.department_id != subject.course.department_id:
            errors["faculty"] = "Faculty member must belong to the subject's department."
        if periods < 1 or periods > 25:
            errors["periods_per_week"] = "Weekly teaching periods must be between 1 and 25."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class FacultyAvailabilitySerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source="faculty.user.get_full_name", read_only=True)
    weekday_name = serializers.CharField(source="get_weekday_display", read_only=True)

    class Meta:
        model = FacultyAvailability
        fields = ("id", "faculty", "faculty_name", "weekday", "weekday_name", "period", "is_available")

    def validate(self, attrs):
        faculty = attrs.get("faculty", getattr(self.instance, "faculty", None))
        weekday = attrs.get("weekday", getattr(self.instance, "weekday", None))
        period = attrs.get("period", getattr(self.instance, "period", None))
        if weekday is not None and not 0 <= weekday <= 4:
            raise serializers.ValidationError({"weekday": "Choose a weekday from Monday through Friday."})
        if period is not None and not 1 <= period <= 8:
            raise serializers.ValidationError({"period": "Choose a period between 1 and 8."})
        if faculty and weekday is not None and period is not None:
            duplicates = FacultyAvailability.objects.filter(
                faculty=faculty, weekday=weekday, period=period
            )
            if self.instance:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError({"period": "Availability for this faculty slot already exists."})
        return attrs

class TimetableEntrySerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source="section.__str__", read_only=True)
    subject_code = serializers.CharField(source="subject.code", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    faculty_name = serializers.CharField(source="faculty.user.get_full_name", read_only=True)
    room_code = serializers.CharField(source="room.code", read_only=True)
    weekday_name = serializers.CharField(source="get_weekday_display", read_only=True)
    semester = serializers.IntegerField(source="section.semester_id", read_only=True)

    class Meta:
        model = TimetableEntry
        fields = (
            "id", "assignment", "section", "section_name", "semester", "subject", "subject_code",
            "subject_name", "faculty", "faculty_name", "room", "room_code", "weekday", "weekday_name",
            "period",
        )


class ExamScheduleSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source="section.__str__", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    room_code = serializers.CharField(source="room.code", read_only=True)
    invigilator_name = serializers.CharField(source="invigilator.user.get_full_name", read_only=True)

    class Meta:
        model = ExamSchedule
        fields = (
            "id", "section", "section_name", "subject", "subject_name", "room", "room_code",
            "invigilator", "invigilator_name", "date", "start_period", "duration_periods",
        )

    def validate(self, attrs):
        schedule = self.instance
        section = attrs.get("section", getattr(schedule, "section", None))
        subject = attrs.get("subject", getattr(schedule, "subject", None))
        room = attrs.get("room", getattr(schedule, "room", None))
        invigilator = attrs.get("invigilator", getattr(schedule, "invigilator", None))
        date = attrs.get("date", getattr(schedule, "date", None))
        start = attrs.get("start_period", getattr(schedule, "start_period", None))
        duration = attrs.get("duration_periods", getattr(schedule, "duration_periods", 1))
        errors = {}
        if section and subject and section.semester_id != subject.semester_id:
            errors["subject"] = "Exam subject must belong to the section's semester."
        if section and room:
            if room.capacity < section.capacity:
                errors["room"] = "Room capacity is below the section capacity."
            if subject and subject.is_lab and not room.is_lab:
                errors["room"] = "A laboratory subject requires a laboratory room."
        if start is not None and duration is not None and start + duration - 1 > 8:
            errors["duration_periods"] = "The exam must finish within the academic day."
        if date and start and duration:
            proposed_periods = set(range(start, start + duration))
            conflicts = ExamSchedule.objects.filter(date=date)
            if schedule:
                conflicts = conflicts.exclude(pk=schedule.pk)
            conflicts = conflicts.filter(
                models.Q(section=section) | models.Q(room=room)
                | (models.Q(invigilator=invigilator) if invigilator else models.Q(pk__in=[]))
            )
            for existing in conflicts:
                occupied = set(range(
                    existing.start_period, existing.start_period + existing.duration_periods
                ))
                if proposed_periods & occupied:
                    errors["start_period"] = "This creates a room, section, or invigilator exam conflict."
                    break
            if not errors:
                date_weekday = date.weekday()
                if 0 <= date_weekday <= 4:
                    timetable_conflicts = TimetableEntry.objects.filter(
                        weekday=date_weekday,
                        period__in=proposed_periods,
                    ).filter(
                        models.Q(section=section)
                        | models.Q(room=room)
                        | (models.Q(faculty=invigilator) if invigilator else models.Q(pk__in=[]))
                    )
                    if timetable_conflicts.exists():
                        errors["start_period"] = "This exam overlaps an existing class timetable entry."
                if not errors and invigilator and 0 <= date.weekday() <= 4:
                    availability = FacultyAvailability.objects.filter(faculty=invigilator)
                    explicit_available = set(
                        availability.filter(is_available=True).values_list("weekday", "period")
                    )
                    if explicit_available:
                        not_available = any(
                            (date.weekday(), period) not in explicit_available
                            for period in proposed_periods
                        )
                    else:
                        unavailable = set(
                            availability.filter(is_available=False).values_list("weekday", "period")
                        )
                        not_available = any(
                            (date.weekday(), period) in unavailable
                            for period in proposed_periods
                        )
                    if not_available:
                        errors["invigilator"] = "The invigilator is unavailable during the exam periods."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class GenerateTimetableSerializer(serializers.Serializer):
    semester = serializers.PrimaryKeyRelatedField(queryset=Semester.objects.select_related("course"))


class TimetableGenerationResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    semester = serializers.IntegerField()
    semester_label = serializers.CharField()
    entry_count = serializers.IntegerField()
    entries = TimetableEntrySerializer(many=True)


class FacultySubstituteSerializer(serializers.Serializer):
    faculty = serializers.IntegerField()
    employee_id = serializers.CharField()
    name = serializers.CharField()
    weekly_assigned_periods = serializers.IntegerField(allow_null=True)


class FacultySubstitutionResponseSerializer(serializers.Serializer):
    timetable_entry = serializers.IntegerField()
    subject = serializers.CharField()
    weekday = serializers.CharField()
    period = serializers.IntegerField()
    suggestions = FacultySubstituteSerializer(many=True)


class DashboardSummarySerializer(serializers.Serializer):
    students = serializers.IntegerField()
    faculty = serializers.IntegerField()
    departments = serializers.IntegerField()
    attendance_rate = serializers.FloatField()
    attendance_records = serializers.IntegerField()
