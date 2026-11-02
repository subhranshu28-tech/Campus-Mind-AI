from django.db import IntegrityError, transaction
from django.db.models import Count, Sum
from django.db.models.deletion import ProtectedError
from django.http import FileResponse
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.accounts.tenancy import scope_queryset, tenant_id_for

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
    TeachingAssignment,
    TimetableEntry,
    SubjectNote,
    PreviousYearQuestionPaper,
)
from .permissions import (
    CampusStaffCanManage,
    IsCampusStudent,
    NotCampusStudent,
    SubjectNotePermission,
)
from .serializers import (
    AcademicYearSerializer,
    AttendanceRecordSerializer,
    ClassroomSerializer,
    CourseSerializer,
    DepartmentSerializer,
    ExamScheduleSerializer,
    FacultySerializer,
    FacultyAvailabilitySerializer,
    FacultySubstitutionResponseSerializer,
    GenerateTimetableSerializer,
    DashboardSummarySerializer,
    SectionSerializer,
    SemesterSerializer,
    StudentSerializer,
    SubjectSerializer,
    TeachingAssignmentSerializer,
    TimetableEntrySerializer,
    TimetableGenerationResponseSerializer,
    SubjectNoteSerializer,
    PreviousYearQuestionPaperSerializer,
)
from .timetable_optimizer import (
    TimetableOptimizationError,
    _faculty_open_slots,
    generate_timetable,
)


class CampusModelViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return scope_queryset(super().get_queryset(), self.request.user)

    permission_classes = [IsAuthenticated, CampusStaffCanManage]

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        college_id = getattr(self.request.user, "college_id", None)
        fields = serializer.child.fields if isinstance(serializer, serializers.ListSerializer) else serializer.fields
        for field in fields.values():
            queryset = getattr(field, "queryset", None)
            if queryset is not None and college_id:
                related_model = queryset.model
                if related_model.__name__ == "User":
                    field.queryset = queryset.filter(college_id=college_id)
                else:
                    lookup = __import__("apps.accounts.tenancy", fromlist=["TENANT_LOOKUPS"]).TENANT_LOOKUPS.get(related_model.__name__)
                    if lookup:
                        field.queryset = queryset.filter(**{lookup: college_id})
        return serializer

    def perform_create(self, serializer):
        college_id = getattr(self.request.user, "college_id", None)
        for value in serializer.validated_data.values():
            if hasattr(value, "_meta") and tenant_id_for(value) != college_id:
                raise ValidationError({"detail": "Related records must belong to your college."})
        save_kwargs = {}
        if any(field.name == "college" for field in serializer.Meta.model._meta.fields):
            save_kwargs["college_id"] = college_id
        serializer.save(**save_kwargs)

    def perform_update(self, serializer):
        college_id = getattr(self.request.user, "college_id", None)
        for value in serializer.validated_data.values():
            if hasattr(value, "_meta") and tenant_id_for(value) != college_id:
                raise ValidationError({"detail": "Related records must belong to your college."})
        serializer.save()

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as error:
            raise ValidationError(
                {"detail": "This record is still referenced by other campus records and cannot be deleted."}
            ) from error


class DepartmentViewSet(CampusModelViewSet):
    queryset = Department.objects.select_related("head").annotate(student_count=Count("students"))
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated, CampusStaffCanManage]
    search_fields = ["name", "code"]
    ordering_fields = ["name", "code", "created_at"]
    filterset_fields = ["is_active"]


class StudentViewSet(CampusModelViewSet):
    queryset = Student.objects.select_related("user", "department", "section__semester__course")
    serializer_class = StudentSerializer
    search_fields = ["student_id", "user__first_name", "user__last_name", "user__email"]
    ordering_fields = ["student_id", "semester", "enrolled_on"]
    filterset_fields = ["department", "semester", "section"]


class FacultyViewSet(CampusModelViewSet):
    queryset = Faculty.objects.select_related("user", "department")
    serializer_class = FacultySerializer
    search_fields = ["employee_id", "qualification", "user__first_name", "user__last_name", "user__email"]
    ordering_fields = ["employee_id", "experience_years"]
    filterset_fields = ["department"]


class AcademicYearViewSet(CampusModelViewSet):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "starts_on", "ends_on"]
    filterset_fields = ["is_active"]


class CourseViewSet(CampusModelViewSet):
    queryset = Course.objects.select_related("department")
    serializer_class = CourseSerializer
    search_fields = ["name", "code", "department__name"]
    ordering_fields = ["name", "code", "duration_years"]
    filterset_fields = ["department", "is_active"]


class SemesterViewSet(CampusModelViewSet):
    queryset = Semester.objects.select_related("course", "academic_year")
    serializer_class = SemesterSerializer
    search_fields = ["course__name", "course__code", "academic_year__name"]
    ordering_fields = ["number"]
    filterset_fields = ["course", "academic_year", "number"]


class SectionViewSet(CampusModelViewSet):
    queryset = Section.objects.select_related("semester__course__department", "semester__academic_year")
    serializer_class = SectionSerializer
    search_fields = ["name", "semester__course__name", "semester__course__code"]
    ordering_fields = ["name", "capacity"]
    filterset_fields = ["semester"]


class SubjectViewSet(CampusModelViewSet):
    queryset = Subject.objects.select_related("course", "semester")
    serializer_class = SubjectSerializer
    search_fields = ["name", "code", "course__name"]
    ordering_fields = ["name", "code", "credits"]
    filterset_fields = ["course", "semester", "is_lab"]


class AttendanceRecordViewSet(CampusModelViewSet):
    queryset = AttendanceRecord.objects.select_related("student__user", "recorded_by")
    serializer_class = AttendanceRecordSerializer
    search_fields = ["student__student_id", "student__user__first_name", "student__user__last_name"]
    ordering_fields = ["date", "created_at"]
    filterset_fields = ["student", "student__department", "date", "is_present"]


class SubjectPDFResourceViewSet(viewsets.ModelViewSet):
    resource_model = None
    serializer_class = None
    permission_classes = [IsAuthenticated, SubjectNotePermission]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        college_id = getattr(self.request.user, "college_id", None)
        if college_id:
            fields = serializer.child.fields if isinstance(serializer, serializers.ListSerializer) else serializer.fields
            for field in fields.values():
                queryset = getattr(field, "queryset", None)
                if queryset is not None:
                    related_model = queryset.model
                    if related_model.__name__ == "User":
                        field.queryset = queryset.filter(college_id=college_id)
                    else:
                        lookup = __import__("apps.accounts.tenancy", fromlist=["TENANT_LOOKUPS"]).TENANT_LOOKUPS.get(related_model.__name__)
                        if lookup:
                            field.queryset = queryset.filter(**{lookup: college_id})
        return serializer

    def get_queryset(self):
        queryset = scope_queryset(self.resource_model.objects.select_related("subject", "uploaded_by"), self.request.user)
        user = self.request.user
        if user.is_staff or user.role in {"super_admin", "college_admin", "hod"}:
            return queryset
        if user.role == "faculty":
            try:
                faculty = user.faculty_record
            except Faculty.DoesNotExist:
                return queryset.none()
            return queryset.filter(subject__teaching_assignments__faculty=faculty).distinct()
        if user.role == "student":
            try:
                student = user.student_record
            except Student.DoesNotExist:
                return queryset.none()
            if not student.section_id:
                return queryset.none()
            return queryset.filter(
                subject__teaching_assignments__section=student.section
            ).distinct()
        return queryset.none()

    def perform_create(self, serializer):
        college_id = getattr(self.request.user, "college_id", None)
        for value in serializer.validated_data.values():
            if hasattr(value, "_meta") and tenant_id_for(value) != college_id:
                raise ValidationError({"detail": "Related records must belong to your college."})
        save_kwargs = {}
        if any(field.name == "college" for field in serializer.Meta.model._meta.fields):
            save_kwargs["college_id"] = college_id
        try:
            serializer.save(uploaded_by=self.request.user, **save_kwargs)
        except IntegrityError as error:
            raise ValidationError({"detail": "The subject PDF could not be saved."}) from error

    def perform_update(self, serializer):
        college_id = getattr(self.request.user, "college_id", None)
        for value in serializer.validated_data.values():
            if hasattr(value, "_meta") and tenant_id_for(value) != college_id:
                raise ValidationError({"detail": "Related records must belong to your college."})
        serializer.save()

    def perform_destroy(self, instance):
        file = instance.file
        instance.delete()
        file.delete(save=False)

    @action(detail=False, methods=["get"])
    def subjects(self, request):
        user = request.user
        if user.role == "faculty":
            try:
                assignments = TeachingAssignment.objects.filter(
                    faculty=user.faculty_record
                ).select_related("subject", "section")
            except Faculty.DoesNotExist as error:
                raise NotFound("No faculty profile is linked to this account.") from error
        elif user.role == "student":
            try:
                section = user.student_record.section
            except Student.DoesNotExist as error:
                raise NotFound("No student profile is linked to this account.") from error
            assignments = TeachingAssignment.objects.filter(section=section).select_related(
                "subject", "section"
            ) if section else TeachingAssignment.objects.none()
        else:
            assignments = TeachingAssignment.objects.filter(
                section__semester__course__department__college_id=user.college_id
            ).select_related("subject", "section")
        subjects = assignments.order_by("subject__code").values(
            "subject_id", "subject__code", "subject__name"
        ).distinct()
        return Response([{
            "id": subject["subject_id"],
            "code": subject["subject__code"],
            "name": subject["subject__name"],
        } for subject in subjects])

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        note = self.get_object()
        response = FileResponse(
            note.file.open("rb"),
            as_attachment=True,
            filename=note.file.name.rsplit("/", 1)[-1],
            content_type="application/pdf",
        )
        return response


class SubjectNoteViewSet(SubjectPDFResourceViewSet):
    resource_model = SubjectNote
    serializer_class = SubjectNoteSerializer


class PreviousYearQuestionPaperViewSet(SubjectPDFResourceViewSet):
    resource_model = PreviousYearQuestionPaper
    serializer_class = PreviousYearQuestionPaperSerializer


class StudentPortalView(APIView):
    permission_classes = [IsAuthenticated, IsCampusStudent]

    def get(self, request):
        try:
            student = Student.objects.select_related(
                "user", "department", "section__semester__course", "section__semester__academic_year"
            ).get(user=request.user)
        except Student.DoesNotExist as error:
            raise NotFound("No student profile is linked to this account.") from error

        attendance = AttendanceRecord.objects.filter(student=student)
        total_sessions = attendance.count()
        present_sessions = attendance.filter(is_present=True).count()
        assignments = TeachingAssignment.objects.filter(section=student.section).select_related(
            "subject", "faculty__user"
        ) if student.section_id else TeachingAssignment.objects.none()
        timetable = TimetableEntry.objects.filter(section=student.section).select_related(
            "assignment", "section__semester__course", "subject", "faculty__user", "room"
        ) if student.section_id else TimetableEntry.objects.none()
        exams = ExamSchedule.objects.filter(
            section=student.section, date__gte=timezone.localdate()
        ).select_related("subject", "room").order_by("date", "start_period") if student.section_id else ExamSchedule.objects.none()

        return Response({
            "student": {
                "student_id": student.student_id,
                "name": student.user.get_full_name() or student.user.username,
                "department": student.department.name,
                "semester": student.semester,
                "section": student.section.name if student.section_id else None,
                "course": student.section.semester.course.name if student.section_id else None,
                "academic_year": student.section.semester.academic_year.name if student.section_id else None,
            },
            "attendance": {
                "total_sessions": total_sessions,
                "present_sessions": present_sessions,
                "absent_sessions": total_sessions - present_sessions,
                "percentage": round(present_sessions / total_sessions * 100, 1) if total_sessions else None,
                "records": AttendanceRecordSerializer(
                    attendance.select_related("recorded_by")[:30], many=True, context={"request": request}
                ).data,
            },
            "subjects": [{
                "id": assignment.subject_id,
                "code": assignment.subject.code,
                "name": assignment.subject.name,
                "credits": assignment.subject.credits,
                "faculty": assignment.faculty.user.get_full_name() or assignment.faculty.user.username,
                "periods_per_week": assignment.periods_per_week,
            } for assignment in assignments],
            "timetable": TimetableEntrySerializer(timetable, many=True).data,
            "exams": ExamScheduleSerializer(exams, many=True).data,
        })


class ClassroomViewSet(CampusModelViewSet):
    queryset = Classroom.objects.all()
    serializer_class = ClassroomSerializer
    search_fields = ["name", "code"]
    ordering_fields = ["code", "name", "capacity"]
    filterset_fields = ["is_lab", "is_active"]


class TeachingAssignmentViewSet(CampusModelViewSet):
    queryset = TeachingAssignment.objects.select_related(
        "section__semester__course", "subject", "faculty__user"
    )
    serializer_class = TeachingAssignmentSerializer
    search_fields = [
        "section__name", "subject__name", "subject__code",
        "faculty__employee_id", "faculty__user__first_name", "faculty__user__last_name",
    ]
    ordering_fields = ["periods_per_week"]
    filterset_fields = ["section", "subject", "faculty"]


class FacultyAvailabilityViewSet(CampusModelViewSet):
    queryset = FacultyAvailability.objects.select_related("faculty__user")
    serializer_class = FacultyAvailabilitySerializer
    search_fields = ["faculty__employee_id", "faculty__user__first_name", "faculty__user__last_name"]
    ordering_fields = ["weekday", "period"]
    filterset_fields = ["faculty", "weekday", "period", "is_available"]


class ExamScheduleViewSet(CampusModelViewSet):
    queryset = ExamSchedule.objects.select_related(
        "section__semester__course", "subject", "room", "invigilator__user"
    )
    serializer_class = ExamScheduleSerializer
    search_fields = ["section__name", "subject__name", "subject__code", "room__code"]
    ordering_fields = ["date", "start_period"]
    filterset_fields = ["date", "section", "room", "invigilator"]


class TimetableEntryViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        return scope_queryset(super().get_queryset(), self.request.user)

    queryset = TimetableEntry.objects.select_related(
        "assignment", "section__semester__course", "subject", "faculty__user", "room"
    )
    serializer_class = TimetableEntrySerializer
    permission_classes = [IsAuthenticated, CampusStaffCanManage]
    filterset_fields = ["section", "section__semester", "faculty", "weekday", "period"]
    ordering_fields = ["weekday", "period"]

    @action(detail=True, methods=["get"])
    @extend_schema(responses=FacultySubstitutionResponseSerializer)
    def substitutions(self, request, pk=None):
        entry = self.get_object()
        qualified_assignments = TeachingAssignment.objects.filter(
            subject=entry.subject
        ).exclude(faculty=entry.faculty)
        candidate_ids = set(qualified_assignments.values_list("faculty_id", flat=True))
        allowed_slots = _faculty_open_slots([
            assignment for assignment in qualified_assignments.select_related("faculty")
            if assignment.faculty_id in candidate_ids
        ])
        busy_ids = set(
            TimetableEntry.objects.filter(
                weekday=entry.weekday, period=entry.period
            ).exclude(pk=entry.pk).values_list("faculty_id", flat=True)
        )
        candidates = Faculty.objects.filter(
            id__in=candidate_ids - busy_ids,
            department=entry.subject.course.department,
        ).select_related("user").annotate(
            weekly_load=Sum("teaching_assignments__periods_per_week")
        )
        suggestions = []
        for faculty in candidates:
            open_slots = allowed_slots.get(faculty.id)
            if open_slots is not None and (entry.weekday, entry.period) not in open_slots:
                continue
            suggestions.append({
                "faculty": faculty.id,
                "employee_id": faculty.employee_id,
                "name": faculty.user.get_full_name() or faculty.user.username,
                "weekly_assigned_periods": faculty.weekly_load or 0,
            })
        suggestions.sort(key=lambda candidate: (
            candidate["weekly_assigned_periods"], candidate["name"].casefold()
        ))
        return Response({
            "timetable_entry": entry.id,
            "subject": entry.subject.code,
            "weekday": entry.get_weekday_display(),
            "period": entry.period,
            "suggestions": suggestions,
        })


class GenerateTimetableView(APIView):
    permission_classes = [IsAuthenticated, CampusStaffCanManage]

    @extend_schema(
        request=GenerateTimetableSerializer,
        responses=TimetableGenerationResponseSerializer,
    )
    @transaction.atomic
    def post(self, request):
        serializer = GenerateTimetableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        semester = serializer.validated_data["semester"]
        if semester.course.department.college_id != request.user.college_id:
            raise ValidationError({"semester": "Semester must belong to your college."})
        try:
            entries = generate_timetable(semester)
        except TimetableOptimizationError as error:
            raise ValidationError({"detail": str(error)}) from error
        TimetableEntry.objects.filter(section__semester=semester).delete()
        TimetableEntry.objects.bulk_create(entries)
        saved = TimetableEntry.objects.filter(section__semester=semester).select_related(
            "assignment", "section__semester__course", "subject", "faculty__user", "room"
        )
        return Response({
            "status": "generated",
            "semester": semester.id,
            "semester_label": str(semester),
            "entry_count": len(entries),
            "entries": TimetableEntrySerializer(saved, many=True).data,
        })


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated, NotCampusStudent]

    @extend_schema(responses=DashboardSummarySerializer)
    def get(self, request):
        attendance_count = scope_queryset(AttendanceRecord.objects.all(), request.user).count()
        present_count = scope_queryset(AttendanceRecord.objects.filter(is_present=True), request.user).count()
        attendance_rate = round(present_count / attendance_count * 100, 1) if attendance_count else 0
        return Response({
            "students": scope_queryset(Student.objects.all(), request.user).count(),
            "faculty": scope_queryset(Faculty.objects.all(), request.user).count(),
            "departments": scope_queryset(Department.objects.filter(is_active=True), request.user).count(),
            "attendance_rate": attendance_rate,
            "attendance_records": attendance_count,
        })
