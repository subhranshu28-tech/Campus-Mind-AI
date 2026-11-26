from rest_framework import serializers

from .models import User


class TenantScopedUniqueNameMixin:
    """Check a ``(college, name)`` unique constraint in the serializer.

    The ``college`` field is read-only on tenant-owned serializers (it is set
    from the session), so DRF skips its automatic ``UniqueTogetherValidator``.
    This mixin restores the friendly validation error instead of letting the
    insert fail with an ``IntegrityError``.
    """

    unique_name_field = "name"
    unique_name_message = "A record with this name already exists in your college."

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        college_id = getattr(getattr(request, "user", None), "college_id", None)
        if college_id:
            name = attrs.get(
                self.unique_name_field,
                getattr(self.instance, self.unique_name_field, None),
            )
            if name is not None:
                queryset = self.Meta.model.objects.filter(
                    college_id=college_id,
                    **{self.unique_name_field: name},
                )
                if self.instance is not None:
                    queryset = queryset.exclude(pk=self.instance.pk)
                if queryset.exists():
                    raise serializers.ValidationError(
                        {self.unique_name_field: self.unique_name_message}
                    )
        return attrs


class CurrentUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "full_name", "role", "is_staff", "college")
