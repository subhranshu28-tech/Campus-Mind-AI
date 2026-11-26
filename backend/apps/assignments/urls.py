from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AssignmentViewSet, SubmissionViewSet

router = DefaultRouter()
router.register("assignments", AssignmentViewSet, basename="assignment")
router.register("submissions", SubmissionViewSet, basename="submission")
urlpatterns = [path("", include(router.urls))]
