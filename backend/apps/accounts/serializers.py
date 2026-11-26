from rest_framework import serializers

from .models import User


class TenantScopedUniqueNameMixin:
    """Check ``(college, <field>)`` unique constraints in the serializer.

    The ``college`` field is read-only on tenant-owned serializers (it is set
    from the session), so DRF skips its automatic ``UniqueTogetherValidator``.
    This mixin restores the friendly validation error instead of letting the
    insert fail with an ``IntegrityError``.
    """

    unique_name_fields = ("name",)
    unique_name_message = "A record with this {field} already exists in your college."

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        college_id = getattr(getattr(request, "user", None), "college_id", None)
        if college_id:
            for field in self.unique_name_fields:
                value = attrs.get(field, getattr(self.instance, field, None))
                if value is None:
                    continue
                queryset = self.Meta.model.objects.filter(
                    college_id=college_id, **{field: value}
                )
                if self.instance is not None:
                    queryset = queryset.exclude(pk=self.instance.pk)
                if queryset.exists():
                    raise serializers.ValidationError(
                        {field: self.unique_name_message.format(field=field)}
                    )
        return attrs


class CurrentUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    schedule_weekdays = serializers.IntegerField(source="college.schedule_weekdays", read_only=True)
    schedule_periods = serializers.IntegerField(source="college.schedule_periods", read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "full_name", "role", "is_staff", "college", "schedule_weekdays", "schedule_periods")
