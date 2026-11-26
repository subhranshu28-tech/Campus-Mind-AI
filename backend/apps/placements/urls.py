from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CompanyViewSet, JobPostingViewSet, PlacementApplicationViewSet

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")
router.register("job-postings", JobPostingViewSet, basename="job-posting")
router.register("placement-applications", PlacementApplicationViewSet, basename="placement-application")
urlpatterns = [path("", include(router.urls))]
