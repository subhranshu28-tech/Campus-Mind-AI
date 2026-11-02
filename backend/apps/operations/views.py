from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.campus.models import Semester, TimetableEntry
from apps.accounts.tenancy import scope_queryset

from . import services
from .models import AuditLog, FacultyLeave, Notification, Substitution
from .permissions import IsCampusManager, IsCampusStaffMember, is_manager
from .serializers import (
    AuditLogSerializer, AutoExamSerializer, FacultyLeaveSerializer, ManualCoverSerializer,
    MoveSerializer, NotificationSerializer, SubstitutionSerializer,
)


class FacultyLeaveViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = FacultyLeaveSerializer
    permission_classes = [IsAuthenticated, IsCampusStaffMember]

    def get_queryset(self):
        queryset = scope_queryset(FacultyLeave.objects.select_related("faculty__user"), self.request.user)
        user = self.request.user
        return queryset if is_manager(user) else queryset.filter(faculty__user=user)

    def perform_create(self, serializer):
        user = self.request.user
        if is_manager(user):
            faculty = serializer.validated_data.get("faculty")
            if faculty is None:
                raise ValidationError({"faculty": "Select the faculty member."})
            if faculty.department.college_id != user.college_id:
                raise ValidationError({"faculty": "Faculty must belong to your college."})
        else:
            faculty = getattr(user, "faculty_record", None)
            if faculty is None:
                raise PermissionDenied("Your account has no faculty profile.")
        leave = serializer.save(faculty=faculty, requested_by=user)
        services.notify(services._managers(user.college_id), "Leave request", f"{services._name(faculty)} requested leave {leave.start_date} to {leave.end_date}.", "leave")
        services.log(user, "leave.requested", "FacultyLeave", leave.id)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsCampusManager])
    def approve(self, request, pk=None):
        leave = self.get_object()
        assigned, unresolved = services.approve_leave(leave, request.user)
        return Response({
            "leave": FacultyLeaveSerializer(leave).data,
            "assigned": SubstitutionSerializer(assigned, many=True).data,
            "unresolved": unresolved,
        })

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsCampusManager])
    def reject(self, request, pk=None):
        leave = self.get_object()
        if leave.status != FacultyLeave.Status.PENDING:
            raise ValidationError({"detail": "Only pending leave can be rejected."})
        leave.status, leave.decided_by, leave.decided_at = "rejected", request.user, timezone.now()
        leave.save(update_fields=["status", "decided_by", "decided_at"])
        services.notify([leave.faculty.user], "Leave rejected", f"Leave {leave.start_date} to {leave.end_date} was not approved.", "leave")
        services.log(request.user, "leave.rejected", "FacultyLeave", leave.id)
        return Response(FacultyLeaveSerializer(leave).data)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated, IsCampusManager])
    def uncovered(self, request, pk=None):
        """Affected classes with no active substitute, each with ranked candidates."""
        leave = self.get_object()
        covered = set(leave.substitutions.filter(status="assigned").values_list("timetable_entry_id", "date"))
        rows = []
        for entry, day in services.affected_classes(leave):
            if (entry.id, day) in covered:
                continue
            rows.append({
                "timetable_entry": entry.id, "date": day, "period": entry.period, "subject": entry.subject.code,
                "section": str(entry.section),
                "candidates": [{"faculty": c["faculty_id"], "name": c["name"], "reason": c["reason"]}
                               for c in services.rank_candidates(entry, day)[:5]],
            })
        return Response(rows)

    @action(detail=True, methods=["post"], url_path="assign-cover", permission_classes=[IsAuthenticated, IsCampusManager])
    def assign_cover(self, request, pk=None):
        serializer = ManualCoverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["faculty"].department.college_id != request.user.college_id:
            raise ValidationError({"faculty": "Faculty must belong to your college."})
        if not scope_queryset(TimetableEntry.objects.all(), request.user).filter(pk=data["timetable_entry"]).exists():
            raise ValidationError({"timetable_entry": "Timetable entry not found in your college."})
        cover = services.assign_manual(self.get_object(), data["timetable_entry"], data["date"], data["faculty"], request.user)
        return Response(SubstitutionSerializer(cover).data, status=status.HTTP_201_CREATED)


class SubstitutionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = SubstitutionSerializer
    permission_classes = [IsAuthenticated, IsCampusStaffMember]

    def get_queryset(self):
        queryset = scope_queryset(Substitution.objects.filter(status="assigned").select_related(
            "subject", "section__semester__course", "room", "original_faculty__user", "substitute__user"), self.request.user)
        user = self.request.user
        if not is_manager(user):
            queryset = queryset.filter(substitute__user=user)
        if self.request.query_params.get("upcoming"):
            queryset = queryset.filter(date__gte=timezone.localdate())
        return queryset


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        unread = Notification.objects.filter(user=request.user, is_read=False).count()
        latest = self.get_queryset()[:30]
        return Response({"unread": unread, "results": self.get_serializer(latest, many=True).data})

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"unread": 0})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        Notification.objects.filter(user=request.user, pk=pk).update(is_read=True)
        return Response({"ok": True})


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsCampusManager]
    def get_queryset(self):
        return scope_queryset(AuditLog.objects.select_related("actor"), self.request.user)


class AnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsCampusStaffMember]

    def get(self, request):
        semester = None
        if request.query_params.get("semester"):
            semester = scope_queryset(Semester.objects.all(), request.user).filter(pk=request.query_params["semester"]).first()
            if semester is None:
                raise ValidationError({"semester": "Semester not found in your college."})
        return Response(services.analytics(semester, college_id=request.user.college_id))


class AutoExamView(APIView):
    permission_classes = [IsAuthenticated, IsCampusManager]

    def post(self, request):
        serializer = AutoExamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["semester"].course.department.college_id != request.user.college_id:
            raise ValidationError({"semester": "Semester must belong to your college."})
        result = services.auto_schedule_exams(
            data["semester"], data["start_date"], data["end_date"], data["holidays"],
            data["avoid_class_clashes"], data["replace_existing"], data["preview"], request.user,
        )
        return Response(result)


class TimetableMoveView(APIView):
    permission_classes = [IsAuthenticated, IsCampusManager]

    def post(self, request, pk):
        entry = scope_queryset(TimetableEntry.objects.select_related("section", "subject", "faculty__user", "room"), request.user).filter(pk=pk).first()
        if entry is None:
            raise ValidationError({"detail": "Timetable entry not found."})
        serializer = MoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["room"].college_id != request.user.college_id:
            raise ValidationError({"room": "Room must belong to your college."})
        problems = services.check_move(entry, data["weekday"], data["period"], data["room"])
        if problems or data["dry_run"]:
            return Response({"ok": not problems, "conflicts": problems, "applied": False})
        services.apply_move(entry, data["weekday"], data["period"], data["room"], request.user)
        return Response({"ok": True, "conflicts": [], "applied": True})


class TimetableExportView(APIView):
    permission_classes = [IsAuthenticated, IsCampusStaffMember]

    def get(self, request):
        scope = request.query_params.get("scope", "section")
        if scope not in {"section", "faculty", "room"}:
            raise ValidationError({"scope": "Use section, faculty or room."})
        try:
            object_id = int(request.query_params.get("id", ""))
        except ValueError:
            raise ValidationError({"id": "Provide the numeric id to export."})
        model_map = {"section": __import__("apps.campus.models", fromlist=["Section"]).Section, "faculty": __import__("apps.campus.models", fromlist=["Faculty"]).Faculty, "room": __import__("apps.campus.models", fromlist=["Classroom"]).Classroom}
        obj = scope_queryset(model_map[scope].objects.all(), request.user).filter(pk=object_id).first()
        if obj is None:
            raise ValidationError({"id": "Record not found in your college."})
        content = services.timetable_workbook(scope, object_id)
        response = HttpResponse(content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="timetable-{scope}-{object_id}.xlsx"'
        return response
