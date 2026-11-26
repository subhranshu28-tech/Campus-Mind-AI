from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BookIssueViewSet, BookViewSet

router = DefaultRouter()
router.register("books", BookViewSet, basename="book")
router.register("book-issues", BookIssueViewSet, basename="book-issue")
urlpatterns = [path("", include(router.urls))]
