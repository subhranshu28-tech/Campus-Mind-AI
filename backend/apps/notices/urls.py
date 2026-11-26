from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CampusEventViewSet, NoticeViewSet

router = DefaultRouter()
router.register("notices", NoticeViewSet, basename="notice")
router.register("events", CampusEventViewSet, basename="campus-event")

urlpatterns = [path("", include(router.urls))]
