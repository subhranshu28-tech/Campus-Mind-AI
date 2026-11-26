from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.token_views import CollegeAwareTokenObtainPairView, LogoutView
from apps.accounts.views import CurrentUserView
from apps.accounts.registration import CollegeRegistrationView
from apps.accounts.security_views import PasswordResetRequestView, PasswordResetConfirmView
from apps.operations.ai_views import CampusAIChatView
from apps.campus.views import (
    AcademicYearViewSet,
    AttendanceRecordViewSet,
    ClassroomViewSet,
    CourseViewSet,
    DashboardSummaryView,
    DepartmentViewSet,
    ExamScheduleViewSet,
    FacultyAvailabilityViewSet,
    FacultyViewSet,
    GenerateTimetableView,
    SectionViewSet,
    SemesterViewSet,
    StudentViewSet,
    StudentPortalView,
    SubjectNoteViewSet,
    PreviousYearQuestionPaperViewSet,
    SubjectViewSet,
    TeachingAssignmentViewSet,
    TimetableEntryViewSet,
)


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "token_refresh"


def health_check(request):
    """Liveness/readiness probe: confirms the database is reachable."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "error", "database": "unavailable"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})


router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("students", StudentViewSet, basename="student")
router.register("faculty", FacultyViewSet, basename="faculty")
router.register("academic-years", AcademicYearViewSet, basename="academic-year")
router.register("courses", CourseViewSet, basename="course")
router.register("semesters", SemesterViewSet, basename="semester")
router.register("sections", SectionViewSet, basename="section")
router.register("subjects", SubjectViewSet, basename="subject")
router.register("attendance", AttendanceRecordViewSet, basename="attendance")
router.register("subject-notes", SubjectNoteViewSet, basename="subject-note")
router.register("question-papers", PreviousYearQuestionPaperViewSet, basename="question-paper")
router.register("classrooms", ClassroomViewSet, basename="classroom")
router.register("teaching-assignments", TeachingAssignmentViewSet, basename="teaching-assignment")
router.register("faculty-availability", FacultyAvailabilityViewSet, basename="faculty-availability")
router.register("exam-schedules", ExamScheduleViewSet, basename="exam-schedule")
router.register("timetable/entries", TimetableEntryViewSet, basename="timetable-entry")

urlpatterns = [
    path("healthz/", health_check, name="health_check"),
    path("admin/", admin.site.urls),
    path("api/auth/register-college/", CollegeRegistrationView.as_view(), name="college_registration"),
    path("api/auth/token/", CollegeAwareTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", ThrottledTokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/logout/", LogoutView.as_view(), name="logout"),
    path("api/auth/me/", CurrentUserView.as_view(), name="current_user"),
    path("api/auth/password-reset/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("api/auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("api/ai/chat/", CampusAIChatView.as_view(), name="campus_ai_chat"),
    path("api/dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard_summary"),
    path("api/student/portal/", StudentPortalView.as_view(), name="student_portal"),
    path("api/timetable/generate/", GenerateTimetableView.as_view(), name="generate_timetable"),
    path("api/", include("apps.operations.urls")),
    path("api/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Serve uploaded media. In DEBUG Django's static() helper is used; in
# production (Render and similar hosts without a dedicated file server) fall
# back to Django's serve view so PDFs and images remain reachable. Put a real
# reverse proxy or object storage in front for high-traffic deployments.
from django.views.static import serve as serve_media
from django.urls import re_path

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve_media, {"document_root": settings.MEDIA_ROOT}),
    ]
