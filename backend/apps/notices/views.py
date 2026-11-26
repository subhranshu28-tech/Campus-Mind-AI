from django.utils import timezone

from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from apps.accounts.tenancy import scope_queryset
from .models import CampusEvent, Notice, NoticeAudience
from .serializers import CampusEventSerializer, NoticeSerializer


class IsNoticeManager(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return user.is_staff or user.role in {"super_admin", "college_admin", "hod"}


def _audience_for(user):
    if user.is_staff or user.role in {"super_admin", "college_admin", "hod"}:
        return None  # managers see everything
    if user.role == "faculty":
        return {NoticeAudience.ALL, NoticeAudience.FACULTY, NoticeAudience.MANAGERS}
    if user.role == "student":
        return {NoticeAudience.ALL, NoticeAudience.STUDENTS}
    return {NoticeAudience.ALL}


class NoticeViewSet(viewsets.ModelViewSet):
    queryset = Notice.objects.all()
    serializer_class = NoticeSerializer
    permission_classes = [IsNoticeManager]

    def get_queryset(self):
        from django.db import models
        queryset = scope_queryset(self.queryset, self.request.user)
        now = timezone.now()
        queryset = queryset.filter(published_at__lte=now)
        queryset = queryset.filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now))
        audience = _audience_for(self.request.user)
        if audience is not None:
            queryset = queryset.filter(audience__in=audience)
        return queryset

    def perform_create(self, serializer):
        college_id = getattr(self.request.user, "college_id", None)
        if not college_id:
            raise PermissionDenied("A college workspace is required.")
        serializer.save(college_id=college_id, created_by=self.request.user)


class CampusEventViewSet(viewsets.ModelViewSet):
    queryset = CampusEvent.objects.all()
    serializer_class = CampusEventSerializer
    permission_classes = [IsNoticeManager]

    def get_queryset(self):
        queryset = scope_queryset(self.queryset, self.request.user)
        audience = _audience_for(self.request.user)
        if audience is not None:
            queryset = queryset.filter(audience__in=audience)
        return queryset

    def perform_create(self, serializer):
        college_id = getattr(self.request.user, "college_id", None)
        if not college_id:
            raise PermissionDenied("A college workspace is required.")
        serializer.save(college_id=college_id, created_by=self.request.user)
