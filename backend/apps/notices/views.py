from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mass_mail
from django.db import models
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from apps.accounts.tenancy import scope_queryset

from .models import CampusEvent, Notice, NoticeAudience
from .serializers import CampusEventSerializer, NoticeSerializer

User = get_user_model()


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
        return None
    if user.role == "faculty":
        return {NoticeAudience.ALL, NoticeAudience.FACULTY}
    if user.role == "student":
        return {NoticeAudience.ALL, NoticeAudience.STUDENTS}
    return {NoticeAudience.ALL}


class NoticeViewSet(viewsets.ModelViewSet):
    queryset = Notice.objects.all()
    serializer_class = NoticeSerializer
    permission_classes = [IsNoticeManager]

    def get_queryset(self):
        queryset = scope_queryset(self.queryset, self.request.user)
        now = timezone.now()
        queryset = queryset.filter(published_at__lte=now).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )
        audience = _audience_for(self.request.user)
        if audience is not None:
            queryset = queryset.filter(audience__in=audience)
        return queryset

    def perform_create(self, serializer):
        college_id = getattr(self.request.user, "college_id", None)
        if not college_id:
            raise PermissionDenied("A college workspace is required.")
        instance = serializer.save(college_id=college_id, created_by=self.request.user)
        self._email_notice(instance)

    def perform_update(self, serializer):
        college_id = getattr(self.request.user, "college_id", None)
        if serializer.instance.college_id != college_id:
            raise PermissionDenied("This resource belongs to a different college.")
        serializer.save()

    def perform_destroy(self, instance):
        college_id = getattr(self.request.user, "college_id", None)
        if instance.college_id != college_id:
            raise PermissionDenied("This resource belongs to a different college.")
        instance.delete()

    def _email_notice(self, notice):
        role_filter = None
        if notice.audience == NoticeAudience.STUDENTS:
            role_filter = ["student"]
        elif notice.audience == NoticeAudience.FACULTY:
            role_filter = ["faculty"]
        elif notice.audience == NoticeAudience.MANAGERS:
            role_filter = ["super_admin", "college_admin", "hod"]
        users = User.objects.filter(college_id=notice.college_id, is_active=True).exclude(email="")
        if role_filter:
            users = users.filter(role__in=role_filter)
        recipients = list(users.values_list("email", flat=True))
        if not recipients:
            return
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@example.invalid"
        message = (f"Campus notice: {notice.title}", notice.body, from_email, recipients)
        try:
            send_mass_mail([message], fail_silently=True)
        except Exception:
            pass


class CampusEventViewSet(viewsets.ModelViewSet):
    queryset = CampusEvent.objects.all()
    serializer_class = CampusEventSerializer
    permission_classes = [IsNoticeManager]

    def get_queryset(self):
        queryset = scope_queryset(self.queryset, self.request.user).filter(ends_at__gte=timezone.now() - timezone.timedelta(days=365))
        audience = _audience_for(self.request.user)
        if audience is not None:
            queryset = queryset.filter(audience__in=audience)
        return queryset

    def perform_create(self, serializer):
        college_id = getattr(self.request.user, "college_id", None)
        if not college_id:
            raise PermissionDenied("A college workspace is required.")
        serializer.save(college_id=college_id, created_by=self.request.user)

    def perform_update(self, serializer):
        college_id = getattr(self.request.user, "college_id", None)
        if serializer.instance.college_id != college_id:
            raise PermissionDenied("This resource belongs to a different college.")
        serializer.save()

    def perform_destroy(self, instance):
        college_id = getattr(self.request.user, "college_id", None)
        if instance.college_id != college_id:
            raise PermissionDenied("This resource belongs to a different college.")
        instance.delete()
