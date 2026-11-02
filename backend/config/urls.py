from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "token_refresh"

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


def health_check(request):
    return HttpResponse("ok")


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
    path("api/auth/token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", ThrottledTokenRefreshView.as_view(), name="token_refresh"),
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
