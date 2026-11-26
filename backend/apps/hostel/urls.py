from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import HostelAllocationViewSet, HostelRoomViewSet, HostelViewSet

router = DefaultRouter()
router.register("hostels", HostelViewSet, basename="hostel")
router.register("hostel-rooms", HostelRoomViewSet, basename="hostel-room")
router.register("hostel-allocations", HostelAllocationViewSet, basename="hostel-allocation")
urlpatterns = [path("", include(router.urls))]
