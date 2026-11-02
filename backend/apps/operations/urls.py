from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import (
    AnalyticsView, AuditLogViewSet, AutoExamView, FacultyLeaveViewSet, NotificationViewSet,
    SubstitutionViewSet, TimetableExportView, TimetableMoveView,
)

router = SimpleRouter()
router.register("leaves", FacultyLeaveViewSet, basename="leave")
router.register("substitutions", SubstitutionViewSet, basename="substitution")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("analytics/overview/", AnalyticsView.as_view(), name="analytics_overview"),
    path("exams/auto-schedule/", AutoExamView.as_view(), name="auto_exam_schedule"),
    path("timetable/entries/<int:pk>/move/", TimetableMoveView.as_view(), name="timetable_move"),
    path("exports/timetable/", TimetableExportView.as_view(), name="timetable_export"),
    path("", include(router.urls)),
]
