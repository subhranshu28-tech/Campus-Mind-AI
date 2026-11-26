"""Reusable, tenant-aware DRF viewsets for college-owned records.

Every ERP module follows the same rules:

* reads are limited to the caller's college (and, for students, to their own
  rows where the module supports it);
* writes require a staff role configured per viewset;
* related objects used on create/update must belong to the same college;
* the owning ``college`` is filled from the authenticated user instead of the
  request body.
"""

from django.db.models.deletion import ProtectedError
from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated

from .tenancy import (
    DEPARTMENT_LOOKUPS,
    TENANT_LOOKUPS,
    department_id_for,
    department_id_for_object,
    scope_queryset,
    tenant_id_for,
)

STAFF_WRITE_ROLES = frozenset({"super_admin", "college_admin", "hod"})


class TenantWritePermission(BasePermission):
    """Any authenticated college member may read; only configured roles write."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        if user.is_staff:
            return True
        if user.role in getattr(view, "write_roles", STAFF_WRITE_ROLES):
            return True
        checker = getattr(view, "student_may_write", None)
        return bool(checker and checker(request))


class TenantModelViewSet(viewsets.ModelViewSet):
    """ModelViewSet that enforces college tenancy on reads and writes."""

    permission_classes = [IsAuthenticated, TenantWritePermission]
    write_roles = STAFF_WRITE_ROLES

    # Students only see their own rows in owned modules. Leave unset for
    # catalog data (fee structures, books, routes, companies, ...).
    student_scope_field = None
    student_scope_by = "pk"  # "pk" compares to Student.pk, "section" to section_id

    def get_queryset(self):
        queryset = scope_queryset(super().get_queryset(), self.request.user)
        if getattr(self.request.user, "role", None) == "student":
            return self._scope_for_student(queryset)
        # Department-level scoping for HODs.
        if getattr(self.request.user, "role", None) == "hod":
            dept_id = department_id_for(self.request.user)
            lookup = DEPARTMENT_LOOKUPS.get(queryset.model.__name__)
            if lookup:
                if dept_id is None:
                    return queryset.none()
                queryset = queryset.filter(**{lookup: dept_id})
        return queryset

    def _scope_for_student(self, queryset):
        field = self.student_scope_field
        if not field:
            return queryset
        from apps.campus.models import Student  # local import: avoids app-load cycles

        student = (
            Student.objects.filter(user=self.request.user)
            .only("pk", "section_id")
            .first()
        )
        if student is None:
            return queryset.none()
        value = student.pk if self.student_scope_by == "pk" else student.section_id
        if value is None:
            return queryset.none()
        return queryset.filter(**{field: value})

    def get_student_profile(self):
        """Return the student linked to the authenticated user (or raise)."""

        from apps.campus.models import Student

        student = Student.objects.select_related("section").filter(
            user=self.request.user
        ).first()
        if student is None:
            raise PermissionDenied("No student profile is linked to this account.")
        return student

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        college_id = getattr(self.request.user, "college_id", None)
        if not college_id:
            return serializer
        fields = (
            serializer.child.fields
            if isinstance(serializer, serializers.ListSerializer)
            else serializer.fields
        )
        for field in fields.values():
            queryset = getattr(field, "queryset", None)
            if queryset is None:
                continue
            related_model = queryset.model
            if related_model.__name__ == "User":
                field.queryset = queryset.filter(college_id=college_id)
                continue
            lookup = TENANT_LOOKUPS.get(related_model.__name__)
            if lookup:
                field.queryset = queryset.filter(**{lookup: college_id})
            if (
                getattr(self.request.user, "role", None) == "hod"
                and related_model.__name__ in DEPARTMENT_LOOKUPS
            ):
                dept_id = department_id_for(self.request.user)
                if dept_id is not None:
                    field.queryset = field.queryset.filter(
                        **{DEPARTMENT_LOOKUPS[related_model.__name__]: dept_id}
                    )
        return serializer

    def _validate_tenant_relations(self, serializer):
        college_id = getattr(self.request.user, "college_id", None)
        if not college_id:
            raise PermissionDenied("A college workspace is required.")
        for value in serializer.validated_data.values():
            if value is None:
                continue
            if hasattr(value, "_meta") and tenant_id_for(value) != college_id:
                raise ValidationError(
                    {"detail": "Related records must belong to your college."}
                )

    def _validate_department_relations(self, serializer):
        user = self.request.user
        if getattr(user, "role", None) != "hod":
            return
        dept_id = department_id_for(user)
        if dept_id is None:
            return
        for value in serializer.validated_data.values():
            if value is None or not hasattr(value, "_meta"):
                continue
            related_dept = department_id_for_object(value)
            if related_dept is not None and related_dept != dept_id:
                raise ValidationError(
                    {"detail": "Related records must belong to your department."}
                )

    def get_create_kwargs(self):
        """Extra ``serializer.save()`` arguments for subclasses."""

        return {}

    def perform_create(self, serializer):
        self._validate_tenant_relations(serializer)
        self._validate_department_relations(serializer)
        kwargs = self.get_create_kwargs()
        if any(field.name == "college" for field in serializer.Meta.model._meta.fields):
            kwargs["college_id"] = self.request.user.college_id
        if (
            getattr(self.request.user, "role", None) == "hod"
            and any(field.name == "department" for field in serializer.Meta.model._meta.fields)
        ):
            dept_id = department_id_for(self.request.user)
            if dept_id is not None:
                kwargs["department_id"] = dept_id
        serializer.save(**kwargs)

    def perform_update(self, serializer):
        self._validate_tenant_relations(serializer)
        self._validate_department_relations(serializer)
        serializer.save()

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as error:
            raise ValidationError(
                {
                    "detail": "This record is still referenced by other campus "
                    "records and cannot be deleted."
                }
            ) from error
