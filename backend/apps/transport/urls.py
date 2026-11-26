from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import StudentTransportViewSet, TransportRouteViewSet, VehicleViewSet

router = DefaultRouter()
router.register("transport-routes", TransportRouteViewSet, basename="transport-route")
router.register("vehicles", VehicleViewSet, basename="vehicle")
router.register("student-transport", StudentTransportViewSet, basename="student-transport")
urlpatterns = [path("", include(router.urls))]
